use super::*;

// Optional deployment mode. Existing upstream installations retain their behavior.
pub(crate) fn projects_root(config: &Config) -> Option<PathBuf> {
    let _ = config;
    env::var("CODEX_WEBUI_PROJECTS_ROOT")
        .ok()
        .filter(|value| !value.trim().is_empty())
        .map(PathBuf::from)
}

async fn checked_projects_root(state: &AppState) -> ApiResult<PathBuf> {
    let root = projects_root(&state.config).ok_or_else(|| {
        api_error(
            StatusCode::BAD_REQUEST,
            "Project workspace is not configured.",
        )
    })?;
    let real = tokio_fs::canonicalize(&root)
        .await
        .map_err(|_| api_error(StatusCode::BAD_REQUEST, "Project root does not exist."))?;
    let roots = resolved_allowed_roots(&state.config).await;
    if !roots.iter().any(|root| path_is_within(root, &real)) {
        return Err(api_error(
            StatusCode::FORBIDDEN,
            "Project root is outside allowed roots.",
        ));
    }
    Ok(real)
}

pub(crate) async fn validate_project_directory(state: &AppState, path: &str) -> ApiResult<PathBuf> {
    let root = checked_projects_root(state).await?;
    let candidate = PathBuf::from(path);
    let metadata = tokio_fs::symlink_metadata(&candidate).await.map_err(|_| {
        api_error(
            StatusCode::BAD_REQUEST,
            "Select an existing project directory.",
        )
    })?;
    let real = tokio_fs::canonicalize(&candidate)
        .await
        .map_err(|_| api_error(StatusCode::BAD_REQUEST, "Project directory is unavailable."))?;
    if metadata.file_type().is_symlink()
        || !metadata.is_dir()
        || real.parent() != Some(root.as_path())
    {
        return Err(api_error(
            StatusCode::FORBIDDEN,
            "Select a specific project inside the workspace root.",
        ));
    }
    Ok(real)
}

pub(crate) async fn list_projects_payload(state: &AppState) -> ApiResult<Value> {
    if projects_root(&state.config).is_none() {
        return Ok(json!({"enabled":false,"projects":[]}));
    }
    let root = checked_projects_root(state).await?;
    let mut entries = tokio_fs::read_dir(&root)
        .await
        .map_err(|e| api_error(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let mut projects = Vec::new();
    while let Ok(Some(entry)) = entries.next_entry().await {
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with('.') {
            continue;
        }
        if entry.file_type().await.is_ok_and(|kind| kind.is_dir()) {
            projects.push(json!({"name":name,"path":entry.path().display().to_string()}));
        }
    }
    projects.sort_by_key(|p| p["name"].as_str().unwrap_or_default().to_lowercase());
    Ok(json!({"enabled":true,"root":root.display().to_string(),"projects":projects}))
}

pub(crate) async fn create_project_payload(
    state: &AppState,
    profile_id: &str,
    name: &str,
) -> ApiResult<Value> {
    let name = name.trim();
    if name.is_empty()
        || name.len() > 120
        || name.starts_with('.')
        || name
            .chars()
            .any(|c| c.is_control() || matches!(c, '/' | '\\' | ':'))
    {
        return Err(api_error(
            StatusCode::BAD_REQUEST,
            "Use a project name without slashes (up to 120 bytes).",
        ));
    }
    let path = checked_projects_root(state).await?.join(name);
    match tokio_fs::create_dir(&path).await {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {
            return Err(api_error(
                StatusCode::CONFLICT,
                "This project already exists. Select it from the list.",
            ));
        }
        Err(e) => return Err(api_error(StatusCode::INTERNAL_SERVER_ERROR, e.to_string())),
    }
    emit_profile_global_notification(
        state,
        profile_id,
        json!({
            "kind":"notification","method":"codex-webui/projectsUpdated","params":{}
        }),
    )
    .await;
    Ok(json!({"name":name,"path":path.display().to_string()}))
}

pub(crate) async fn list_project_files_payload(
    state: &AppState,
    project: &str,
    path: Option<&str>,
) -> ApiResult<Value> {
    let project = validate_project_directory(state, project).await?;
    let requested = path
        .filter(|p| !p.is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(|| project.clone());
    let directory = tokio_fs::canonicalize(requested)
        .await
        .map_err(|_| api_error(StatusCode::BAD_REQUEST, "Directory is unavailable."))?;
    if !path_is_within(&project, &directory) {
        return Err(api_error(
            StatusCode::FORBIDDEN,
            "Path is outside this project.",
        ));
    }
    ensure_not_sensitive_file_path(&directory)?;
    let mut reader = tokio_fs::read_dir(&directory)
        .await
        .map_err(|_| api_error(StatusCode::BAD_REQUEST, "Cannot list this directory."))?;
    let mut entries = Vec::new();
    let mut truncated = false;
    while let Ok(Some(entry)) = reader.next_entry().await {
        let path = entry.path();
        if ensure_not_sensitive_file_path(&path).is_err() {
            continue;
        }
        let Ok(meta) = tokio_fs::symlink_metadata(&path).await else {
            continue;
        };
        // Do not follow symlinks from a project file listing.
        if meta.file_type().is_symlink() || !(meta.is_dir() || meta.is_file()) {
            continue;
        }
        if entries.len() == 500 {
            truncated = true;
            break;
        }
        entries.push(json!({"name":entry.file_name().to_string_lossy(),"path":path.display().to_string(),"isDirectory":meta.is_dir(),"size":meta.len()}));
    }
    entries.sort_by_key(|p| {
        (
            !p["isDirectory"].as_bool().unwrap_or(false),
            p["name"].as_str().unwrap_or_default().to_lowercase(),
        )
    });
    Ok(
        json!({"path":directory.display().to_string(),"parent":if directory == project {None} else {directory.parent().map(|p|p.display().to_string())},"entries":entries,"truncated":truncated}),
    )
}

// Keep the attachment snapshot in private runtime storage; expose an editable copy
// in the project. Immutable snapshots keep historical attachment downloads stable.
pub(crate) async fn copy_attachment_into_project(
    state: &AppState,
    profile_id: &str,
    session_id: &str,
    record: &StoredAttachmentRecord,
) -> ApiResult<Option<String>> {
    if projects_root(&state.config).is_none() {
        return Ok(None);
    }
    let ui = with_ui_state_read(state, profile_id, |ui| Ok(ui.clone()))
        .await
        .map_err(|e| api_error(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let cwd = ui
        .get("preferencesByThreadId")
        .and_then(|v| v.get(session_id))
        .and_then(|v| v.get("cwd"))
        .and_then(Value::as_str)
        .ok_or_else(|| api_error(StatusCode::BAD_REQUEST, "The session has no project."))?;
    let project = validate_project_directory(state, cwd).await?;
    let uploads = project.join("uploads");
    if let Ok(meta) = tokio_fs::symlink_metadata(&uploads).await {
        if meta.file_type().is_symlink() || !meta.is_dir() {
            return Err(api_error(
                StatusCode::FORBIDDEN,
                "Project uploads must be a real directory.",
            ));
        }
    } else {
        tokio_fs::create_dir(&uploads)
            .await
            .map_err(|e| api_error(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    }
    let source = PathBuf::from(record.path.as_deref().unwrap_or_default());
    let safe_name: String = record
        .original_name
        .chars()
        .map(|c| {
            if c.is_alphanumeric() || matches!(c, '.' | '_' | '-') {
                c
            } else {
                '-'
            }
        })
        .take(60)
        .collect();
    let target = uploads.join(format!("{}-{}", record.id, safe_name));
    let mut input = tokio_fs::File::open(&source)
        .await
        .map_err(|e| api_error(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let mut output = tokio_fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&target)
        .await
        .map_err(|e| api_error(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    if let Err(error) = tokio::io::copy(&mut input, &mut output).await {
        let _ = tokio_fs::remove_file(&target).await;
        return Err(api_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            error.to_string(),
        ));
    }
    output
        .sync_all()
        .await
        .map_err(|e| api_error(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Some(target.display().to_string()))
}
