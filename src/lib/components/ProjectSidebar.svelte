<script lang="ts">
  import { onMount } from 'svelte';
  import { Plus, FolderOpen, Folder, File, ArrowUp, RefreshCw, MessageSquare, Settings, LogOut, X, Paperclip, Download, AtSign, Moon, Sun, ChevronRight, Search } from 'lucide-svelte';
  import { api } from '$lib/api';
  import type { SessionSummary, WsConnectionState } from '$lib/types';
  let { projects, root, selectedProject, sessions, selectedId, connectionState, mobile = false, readOnly = false,
    onSelectProject, onCreateProject, onCreateSession, onSelectSession, onClose, onOpenFile, onReference, onUpload, onSettings, onLogout, onTheme, dark = false, onLoadMore, hasMore = false, archived = false, onArchivedChange
  }: {
    projects: Array<{name:string;path:string}>; root:string; selectedProject:string; sessions:SessionSummary[]; selectedId:string|null; connectionState:WsConnectionState;
    archived?:boolean; onArchivedChange:(archived:boolean)=>void; mobile?:boolean; readOnly?:boolean; dark?:boolean; hasMore?:boolean;
    onSelectProject:(path:string)=>void; onCreateProject:(name:string)=>Promise<void>; onCreateSession:()=>void; onSelectSession:(id:string)=>void;
    onClose:()=>void; onOpenFile:(path:string)=>void; onReference:(path:string)=>void; onUpload:()=>void; onSettings:()=>void; onLogout:()=>void; onTheme:()=>void; onLoadMore:()=>void;
  } = $props();
  let creating = $state(false), name = $state(''), busy = $state(false), error = $state(''), query = $state('');
  let section = $state<'chats'|'files'>('chats');
  let files = $state<Awaited<ReturnType<typeof api.listProjectFiles>>|null>(null);
  let fileBusy = $state(false), fileError = $state('');
  let requestVersion = 0;
  const visible = $derived(sessions.filter(s => s.cwd === selectedProject && (!query || `${s.name ?? ''} ${s.preview ?? ''}`.toLowerCase().includes(query.toLowerCase()))));
  const projectName = $derived(projects.find(p=>p.path===selectedProject)?.name ?? '选择项目');
  const statusLabel = (s:SessionSummary) => ['active','running','inProgress','starting'].includes(s.status) ? '运行中' : s.status === 'failed' ? '失败' : ['waiting','waitingForApproval','waitingForInput'].includes(s.status) ? '等待操作' : '已保存';
  const displayFileName = (name:string) => name.replace(/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}-/i, "");
  const size = (n:number) => n < 1024 ? `${n} B` : n < 1048576 ? `${(n/1024).toFixed(1)} KB` : `${(n/1048576).toFixed(1)} MB`;
  async function create() {
    if (!name.trim() || busy) return;
    busy=true;error='';
    try { await onCreateProject(name.trim()); creating=false;name='';section='chats'; } catch(e){ error=e instanceof Error?e.message:String(e); } finally{busy=false;}
  }
  async function browse(path?:string) {
    const version=++requestVersion;
    if (!selectedProject) { files=null;return; }
    fileBusy=true;fileError='';
    try { const result=await api.listProjectFiles(selectedProject,path); if(version===requestVersion) files=result; }
    catch(e){if(version===requestVersion)fileError=e instanceof Error?e.message:String(e);}
    finally{if(version===requestVersion)fileBusy=false;}
  }
  async function download(path:string) {
    try {const {blob,filename}=await api.downloadEditableFile(path);const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename??path.split("/").at(-1)??"download";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    catch(e){fileError=e instanceof Error?e.message:String(e);}
  }
  $effect(()=>{const project=selectedProject;if(project){files=null;void browse(project);}else{files=null;}});
  onMount(()=>{const timer=setInterval(()=>{if(section==='files'&&selectedProject&&document.visibilityState==='visible')void browse(files?.path);},10000);return()=>clearInterval(timer);});
</script>

<div class="project-sidebar">
  <div class="wb-brand"><span class="wb-mark">C</span><div><strong>Codex 工作台</strong><small>DGX · 个人项目</small></div>{#if mobile}<button class="wb-icon" onclick={onClose} aria-label="关闭导航"><X size={18}/></button>{/if}</div>
  <div class="wb-connection"><span class:online={connectionState==='connected'}></span>{connectionState==='connected'?'已连接 · 任务在 DGX 运行':connectionState==='reconnecting'?'正在重连，任务继续运行':'正在连接 DGX'}</div>
  <div class="wb-projects">
    <div class="wb-label"><span>项目空间</span><button class="wb-icon" title="创建真实项目文件夹" aria-label="新建项目" disabled={readOnly} onclick={()=>{creating=!creating;error='';}}><Plus size={17}/></button></div>
    <label class="wb-select"><FolderOpen size={17}/><select aria-label="当前项目" value={selectedProject} onchange={e=>{onSelectProject(e.currentTarget.value);section='chats';}}><option value="" disabled>选择一个项目</option>{#each projects as project}<option value={project.path}>{project.name}</option>{/each}</select></label>
    {#if creating}<form class="wb-create" onsubmit={e=>{e.preventDefault();void create();}}><label for="project-name">项目名称</label><input id="project-name" bind:value={name} placeholder="例如：旅行计划" maxlength="80" autocomplete="off"/><p>将在项目空间内创建真实文件夹。</p><div><button class="wb-secondary" type="button" onclick={()=>creating=false}>取消</button><button class="wb-primary" disabled={busy||!name.trim()}>{busy?'创建中…':'创建项目'}</button></div>{#if error}<p role="alert" class="wb-error">{error}</p>{/if}</form>{/if}
    {#if !projects.length&&!creating}<p class="wb-empty">先创建一个项目。每个项目有独立文件夹，可以包含多条对话。</p><button class="wb-primary" onclick={()=>creating=true}>创建第一个项目</button>{/if}
    {#if selectedProject}<p class="wb-location" title={selectedProject}>{selectedProject}</p>{/if}
    <button class="wb-new-chat" onclick={onCreateSession} disabled={!selectedProject||readOnly}><Plus size={17}/> 新对话</button>
  </div>
  <div class="wb-tabs" role="tablist" aria-label="项目内容"><button role="tab" aria-selected={section==='chats'} class:active={section==='chats'} onclick={()=>section='chats'}><MessageSquare size={15}/>对话 <span>{visible.length}</span></button><button role="tab" aria-selected={section==='files'} class:active={section==='files'} onclick={()=>{section='files';void browse();}}><Folder size={15}/>文件</button></div>
  {#if section==='chats'}
    <div class="wb-search"><button class="wb-icon" title={archived?"查看未归档对话":"查看归档对话"} aria-label={archived?"查看未归档对话":"查看归档对话"} onclick={()=>onArchivedChange(!archived)}>{archived?"归档":"全部"}</button><Search size={15}/><input aria-label="搜索本项目对话" placeholder="搜索对话" bind:value={query}/></div>
    <div class="wb-chat-list">
      {#each visible as session (session.id)}<button class="wb-chat" class:selected={session.id===selectedId} onclick={()=>onSelectSession(session.id)}><strong>{session.name || session.preview || '新对话'}</strong><small><span class:running={statusLabel(session)==='运行中'}>{statusLabel(session)}</span><span>{session.preview?.slice(0,55) ?? ''}</span></small></button>{/each}
      {#if !visible.length}<p class="wb-empty">{selectedProject?(archived?'这个项目没有归档对话。':'这个项目还没有对话。点击“新对话”开始。'):'选择项目后查看对话。'}</p>{/if}
      {#if hasMore}<button class="wb-secondary wb-load" onclick={onLoadMore}>加载更多对话</button>{/if}
    </div>
  {:else}
    <div class="wb-file-toolbar"><button class="wb-icon" disabled={!files?.parent} onclick={()=>void browse(files?.parent??undefined)} aria-label="上一级文件夹"><ArrowUp size={17}/></button><span title={files?.path}>{files?.path===selectedProject?projectName:files?.path.split('/').at(-1)??'项目文件'}</span><button class="wb-icon" onclick={()=>void browse(files?.path)} aria-label="刷新文件"><RefreshCw size={16} class={fileBusy?'animate-spin':''}/></button><button class="wb-icon" disabled={!selectedProject||readOnly} onclick={onUpload} aria-label="上传到当前对话" title="上传文件并附加到当前对话"><Paperclip size={17}/></button></div>
    <div class="wb-file-list">
      {#if fileError}<p role="alert" class="wb-error">{fileError}</p>{/if}
      {#each files?.entries ?? [] as file (file.path)}<div class="wb-file-row"><button class="wb-file-name" title={file.path} onclick={()=>file.isDirectory?void browse(file.path):onOpenFile(file.path)}>{#if file.isDirectory}<Folder size={17}/>{:else}<File size={17}/>{/if}<span>{displayFileName(file.name)}<small>{file.isDirectory?'文件夹':size(file.size)}</small></span>{#if file.isDirectory}<ChevronRight size={14}/>{/if}</button>{#if !file.isDirectory}<button class="wb-icon" onclick={()=>onReference(file.path)} aria-label={`引用 ${file.name}`} title="加入聊天输入框"><AtSign size={15}/></button><button class="wb-icon" onclick={()=>void download(file.path)} aria-label={`下载 ${file.name}`} title="下载"><Download size={15}/></button>{/if}</div>{/each}
      {#if !fileBusy&&!files?.entries.length&&!fileError}<p class="wb-empty">项目文件会显示在这里。上传的文件保存在项目的 uploads 文件夹。</p>{/if}
      {#if files?.truncated}<p class="wb-empty">此目录较大，显示前 500 项。</p>{/if}
    </div>
  {/if}
  <footer class="wb-sidebar-footer"><button class="wb-icon" onclick={onSettings} aria-label="设置" title="设置"><Settings size={18}/></button><span title={root}>个人远程工作空间</span><button class="wb-icon" onclick={onTheme} aria-label="切换深浅色" title="切换深浅色">{#if dark}<Sun size={18}/>{:else}<Moon size={18}/>{/if}</button><button class="wb-icon" onclick={onLogout} aria-label="退出 WebUI" title="退出 WebUI"><LogOut size={17}/></button></footer>
</div>
