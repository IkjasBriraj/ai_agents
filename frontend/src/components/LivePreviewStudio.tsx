import React, { useState, useEffect, useRef, useCallback } from 'react';
import { OllamaService } from '@/services/ollama';
import { Button } from '@/components/ui/button';
import {
  Monitor,
  Tablet,
  Smartphone,
  Laptop,
  Maximize2,
  Minimize2,
  RefreshCw,
  Code2,
  Eye,
  Columns,
  Save,
  FolderOpen,
  FileCode,
  ExternalLink,
  Sparkles,
  Play,
  Check,
  Upload,
  ChevronRight,
  ChevronLeft,
  Layers,
  GripVertical,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface WorkspaceFileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
}

interface LivePreviewStudioProps {
  initialFilePath?: string | null;
}

const DEFAULT_STARTER_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SeniorAgent Live Preview Studio</title>
  <style>
    :root {
      --bg: #090d16;
      --card: rgba(15, 23, 42, 0.78);
      --accent: #3b82f6;
      --purple: #8b5cf6;
      --emerald: #10b981;
      --text: #f8fafc;
      --muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: radial-gradient(circle at 15% 15%, rgba(59, 130, 246, 0.18), transparent 45%),
                  radial-gradient(circle at 85% 20%, rgba(139, 92, 246, 0.18), transparent 45%),
                  var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }
    .studio-card {
      max-width: 720px;
      width: 100%;
      background: var(--card);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 24px;
      padding: 2.5rem;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.45);
      animation: floatIn 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes floatIn {
      from { opacity: 0; transform: translateY(16px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: 999px;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.4);
      color: #60a5fa;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      margin-bottom: 1.25rem;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--emerald);
      box-shadow: 0 0 12px var(--emerald);
    }
    h1 {
      font-size: 2.25rem;
      line-height: 1.2;
      font-weight: 800;
      background: linear-gradient(135deg, #ffffff 0%, #93c5fd 50%, #c4b5fd 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 0.85rem;
    }
    p {
      color: var(--muted);
      line-height: 1.65;
      font-size: 1rem;
      margin-bottom: 1.75rem;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 1.75rem;
    }
    .metric {
      padding: 1.1rem;
      border-radius: 16px;
      background: rgba(30, 41, 59, 0.55);
      border: 1px solid rgba(148, 163, 184, 0.14);
      transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric:hover {
      transform: translateY(-3px);
      border-color: rgba(59, 130, 246, 0.5);
    }
    .metric-val {
      font-size: 1.35rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 0.25rem;
    }
    .metric-lbl {
      font-size: 0.78rem;
      color: var(--muted);
    }
    button {
      background: linear-gradient(135deg, var(--accent), var(--purple));
      color: white;
      border: none;
      padding: 0.85rem 1.6rem;
      border-radius: 12px;
      font-weight: 600;
      font-size: 0.92rem;
      cursor: pointer;
      transition: all 0.2s ease;
      box-shadow: 0 10px 25px rgba(59, 130, 246, 0.3);
    }
    button:hover {
      transform: translateY(-2px);
      box-shadow: 0 14px 30px rgba(139, 92, 246, 0.45);
    }
  </style>
</head>
<body>
  <div class="studio-card">
    <div class="badge"><span class="dot"></span> Interactive Live Preview Studio</div>
    <h1>Real-Time Web & App Canvas</h1>
    <p>
      Select any generated HTML/CSS/JS file from your agent workspace on the left, drag & drop a file onto this canvas, or edit the live code in split-screen mode.
    </p>
    <div class="grid">
      <div class="metric">
        <div class="metric-val" id="counter">100%</div>
        <div class="metric-lbl">Hot-Reload Sandbox</div>
      </div>
      <div class="metric">
        <div class="metric-val">4 Viewports</div>
        <div class="metric-lbl">Desktop • Laptop • Tablet • Mobile</div>
      </div>
      <div class="metric">
        <div class="metric-val">Auto-Bundle</div>
        <div class="metric-lbl">Inlines Workspace CSS & JS</div>
      </div>
    </div>
    <button onclick="triggerPulse()">Test Interactive JS Pulse ✨</button>
  </div>
  <script>
    let clicks = 0;
    function triggerPulse() {
      clicks++;
      const el = document.getElementById('counter');
      el.textContent = 'Active #' + clicks;
      el.style.color = '#34d399';
    }
  </script>
</body>
</html>`;

export const LivePreviewStudio: React.FC<LivePreviewStudioProps> = ({ initialFilePath }) => {
  const [currentDir, setCurrentDir] = useState<string>('');
  const [workspaceRoot, setWorkspaceRoot] = useState<string>('');
  const [items, setItems] = useState<WorkspaceFileItem[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(initialFilePath || null);
  const [selectedFileName, setSelectedFileName] = useState<string>('starter-preview.html');
  const [rawCode, setRawCode] = useState<string>(DEFAULT_STARTER_HTML);
  const [renderedSrcDoc, setRenderedSrcDoc] = useState<string>(DEFAULT_STARTER_HTML);
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(false);

  // Layout & Extend / Viewport states
  const [viewMode, setViewMode] = useState<'split' | 'preview' | 'code'>('split');
  const [deviceViewport, setDeviceViewport] = useState<'desktop' | 'laptop' | 'tablet' | 'mobile'>('desktop');
  const [isExtendedFullscreen, setIsExtendedFullscreen] = useState(false);
  const [showFileSidebar, setShowFileSidebar] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  // Smooth Draggable Split-Pane state
  const [splitRatio, setSplitRatio] = useState<number>(42); // percentage for Code pane in split mode
  const [isDraggingSplit, setIsDraggingSplit] = useState<boolean>(false);
  const splitContainerRef = useRef<HTMLDivElement>(null);

  // Drag-and-Drop File onto Preview Studio
  const [isDraggingFileOver, setIsDraggingFileOver] = useState(false);

  // Load workspace directory
  const loadDirectory = useCallback(async (dirPath?: string) => {
    setLoadingFiles(true);
    try {
      let target = dirPath;
      if (!target) {
        const roots = await OllamaService.getWorkspaceRoots();
        if (roots?.workspace) {
          target = roots.workspace;
          setWorkspaceRoot(roots.workspace);
        }
      }
      if (target) {
        const res = await OllamaService.getWorkspaceList(target);
        if (res && res.status === 'success') {
          setCurrentDir(res.path);
          const sorted = [...(res.items || [])].sort((a, b) => {
            if (a.is_dir && !b.is_dir) return -1;
            if (!a.is_dir && b.is_dir) return 1;
            return a.name.localeCompare(b.name);
          });
          setItems(sorted);

          // Auto-select the first HTML file if no file is selected yet
          if (!selectedFilePath) {
            const firstHtml = sorted.find((it) => !it.is_dir && it.name.toLowerCase().endsWith('.html'));
            if (firstHtml) {
              handleSelectFile(firstHtml.path, firstHtml.name, sorted);
            }
          }
        }
      }
    } catch (e) {
      console.error('Failed to load workspace for preview:', e);
    } finally {
      setLoadingFiles(false);
    }
  }, [selectedFilePath]);

  // Bundle relative CSS and JS files from the same workspace folder into srcDoc
  const bundleHtmlWithAssets = useCallback(async (htmlContent: string, filePath: string | null, _dirItems?: WorkspaceFileItem[]) => {
    if (!filePath) {
      setRenderedSrcDoc(htmlContent);
      return;
    }
    let bundled = htmlContent;
    const folderPath = filePath.replace(/[\\/][^\\/]+$/, '');

    try {
      // Inline relative <link rel="stylesheet" href="...">
      const cssRegex = /<link[^>]+href=["']([^"':]+\.css)["'][^>]*>/gi;
      const cssMatches = [...bundled.matchAll(cssRegex)];
      for (const match of cssMatches) {
        const relHref = match[1].replace(/^\.\//, '');
        const targetPath = `${folderPath}/${relHref}`;
        try {
          const cssRes = await OllamaService.getWorkspaceFile(targetPath);
          if (cssRes?.status === 'success' && typeof cssRes.content === 'string') {
            bundled = bundled.replace(match[0], `<style data-inlined="${relHref}">\n${cssRes.content}\n</style>`);
          }
        } catch {
          // keep original link if not found
        }
      }

      // Inline relative <script src="..."></script>
      const jsRegex = /<script[^>]+src=["']([^"':]+\.js)["'][^>]*>\s*<\/script>/gi;
      const jsMatches = [...bundled.matchAll(jsRegex)];
      for (const match of jsMatches) {
        const relSrc = match[1].replace(/^\.\//, '');
        const targetPath = `${folderPath}/${relSrc}`;
        try {
          const jsRes = await OllamaService.getWorkspaceFile(targetPath);
          if (jsRes?.status === 'success' && typeof jsRes.content === 'string') {
            bundled = bundled.replace(match[0], `<script data-inlined="${relSrc}">\n${jsRes.content}\n</script>`);
          }
        } catch {
          // keep original script tag if not found
        }
      }
    } catch {
      // fallback
    }
    setRenderedSrcDoc(bundled);
  }, []);

  const handleSelectFile = async (path: string, name: string, dirItemsOverride?: WorkspaceFileItem[]) => {
    try {
      const res = await OllamaService.getWorkspaceFile(path);
      if (res && res.status === 'success') {
        const content = res.content || '';
        setSelectedFilePath(path);
        setSelectedFileName(name);
        setRawCode(content);

        if (name.toLowerCase().endsWith('.html') || name.toLowerCase().endsWith('.htm')) {
          await bundleHtmlWithAssets(content, path, dirItemsOverride || items);
        } else if (name.toLowerCase().endsWith('.css')) {
          // Wrap standalone CSS in a preview harness
          setRenderedSrcDoc(`<!DOCTYPE html><html><head><style>${content}</style></head><body style="padding:2rem;font-family:sans-serif;"><h2>CSS Stylesheet Preview (${name})</h2><p>Edit CSS on the left to test rules live.</p><div class="card container box"><button>Sample Button</button></div></body></html>`);
        } else {
          // Display code or markdown formatted in preview
          const escaped = content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          setRenderedSrcDoc(`<!DOCTYPE html><html><head><style>body{background:#090d16;color:#e2e8f0;font-family:'IBM Plex Mono',monospace;padding:1.5rem;font-size:13px;line-height:1.6;}pre{white-space:pre-wrap;word-break:break-word;}</style></head><body><pre>${escaped}</pre></body></html>`);
        }
      }
    } catch (e) {
      console.error('Error loading file in preview studio:', e);
    }
  };

  useEffect(() => {
    loadDirectory();
  }, []);

  useEffect(() => {
    if (initialFilePath) {
      const parts = initialFilePath.split(/[\\/]/);
      const fname = parts[parts.length - 1] || 'index.html';
      handleSelectFile(initialFilePath, fname);
    }
  }, [initialFilePath]);

  // Live update preview when rawCode changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (selectedFileName.toLowerCase().endsWith('.html') || !selectedFilePath) {
        bundleHtmlWithAssets(rawCode, selectedFilePath, items);
      }
    }, 220);
    return () => clearTimeout(timer);
  }, [rawCode, selectedFilePath, selectedFileName, items, bundleHtmlWithAssets]);

  // Handle Draggable Split Divider
  useEffect(() => {
    if (!isDraggingSplit) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!splitContainerRef.current) return;
      const rect = splitContainerRef.current.getBoundingClientRect();
      const relX = e.clientX - rect.left;
      const pct = Math.min(78, Math.max(22, (relX / rect.width) * 100));
      setSplitRatio(pct);
    };

    const handleMouseUp = () => {
      setIsDraggingSplit(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingSplit]);

  const handleSave = async () => {
    if (!selectedFilePath) return;
    setIsSaving(true);
    try {
      await OllamaService.writeWorkspaceFile(selectedFilePath, rawCode);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2000);
    } catch (e) {
      console.error('Failed to save file:', e);
    } finally {
      setIsSaving(false);
    }
  };

  const handleOpenInNewTab = () => {
    const blob = new Blob([renderedSrcDoc], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  };

  const handleDropFile = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingFileOver(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const text = await file.text();
    setSelectedFilePath(null);
    setSelectedFileName(file.name);
    setRawCode(text);
    setRenderedSrcDoc(text);
  };

  const viewportWidthClass =
    deviceViewport === 'desktop'
      ? 'w-full'
      : deviceViewport === 'laptop'
      ? 'w-[1024px] max-w-full'
      : deviceViewport === 'tablet'
      ? 'w-[768px] max-w-full'
      : 'w-[390px] max-w-full';

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDraggingFileOver(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget.contains(e.relatedTarget as Node)) return;
        setIsDraggingFileOver(false);
      }}
      onDrop={handleDropFile}
      className={cn(
        "flex flex-col border border-border/80 bg-card/90 backdrop-blur-2xl rounded-2xl shadow-2xl overflow-hidden transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
        isExtendedFullscreen
          ? "fixed inset-3 z-[100] h-[calc(100vh-24px)] ring-2 ring-primary/50 shadow-[0_0_80px_rgba(59,130,246,0.35)] animate-in zoom-in-95 duration-300"
          : "h-[calc(100vh-190px)] min-h-[720px] relative"
      )}
    >
      {/* Magnetic Drag-and-Drop Overlay */}
      {isDraggingFileOver && (
        <div className="absolute inset-0 z-50 bg-slate-950/85 backdrop-blur-xl border-4 border-dashed border-primary rounded-2xl flex flex-col items-center justify-center pointer-events-none animate-in fade-in zoom-in-95 duration-200">
          <div className="w-20 h-20 rounded-2xl bg-primary/20 border border-primary/50 flex items-center justify-center shadow-[0_0_40px_rgba(59,130,246,0.5)] animate-bounce">
            <Upload className="w-10 h-10 text-primary" />
          </div>
          <h3 className="text-xl font-bold text-white mt-4">Drop HTML, CSS, or Code File to Preview Live</h3>
          <p className="text-xs text-slate-300 mt-1">Instant zero-latency rendering inside the interactive sandbox</p>
        </div>
      )}

      {/* TOP STUDIO TOOLBAR */}
      <div className="h-14 px-4 border-b border-border/70 bg-secondary/40 flex flex-wrap items-center justify-between gap-3 shrink-0">
        {/* Left: Sidebar Toggle & Active File Pill */}
        <div className="flex items-center gap-2.5 min-w-0">
          <button
            onClick={() => setShowFileSidebar(!showFileSidebar)}
            className="p-2 rounded-lg border border-border bg-card hover:bg-secondary text-muted-foreground hover:text-foreground transition-all cursor-pointer"
            title={showFileSidebar ? "Hide Workspace Files" : "Show Workspace Files"}
          >
            {showFileSidebar ? <ChevronLeft className="w-4 h-4" /> : <FolderOpen className="w-4 h-4 text-primary" />}
          </button>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-background/80 border border-border/80 min-w-0">
            <FileCode className="w-4 h-4 text-primary shrink-0" />
            <span className="font-mono text-xs font-semibold text-foreground truncate max-w-[200px]">
              {selectedFileName}
            </span>
            {selectedFilePath && (
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                Workspace
              </span>
            )}
          </div>
        </div>

        {/* Center: View Mode & Responsive Device Switcher */}
        <div className="flex items-center gap-3">
          {/* Split / Preview / Code Switcher */}
          <div className="flex items-center bg-background/80 p-1 rounded-xl border border-border/80">
            <button
              onClick={() => setViewMode('preview')}
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all cursor-pointer",
                viewMode === 'preview' ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Preview</span>
            </button>
            <button
              onClick={() => setViewMode('split')}
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all cursor-pointer",
                viewMode === 'split' ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Split Studio</span>
            </button>
            <button
              onClick={() => setViewMode('code')}
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all cursor-pointer",
                viewMode === 'code' ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>Code</span>
            </button>
          </div>

          {/* Device Viewport Selector */}
          <div className="hidden md:flex items-center bg-background/80 p-1 rounded-xl border border-border/80">
            {[
              { id: 'desktop', icon: Monitor, label: '100%' },
              { id: 'laptop', icon: Laptop, label: '1024px' },
              { id: 'tablet', icon: Tablet, label: '768px' },
              { id: 'mobile', icon: Smartphone, label: '390px' },
            ].map((dev) => {
              const DevIcon = dev.icon;
              const active = deviceViewport === dev.id;
              return (
                <button
                  key={dev.id}
                  onClick={() => setDeviceViewport(dev.id as any)}
                  className={cn(
                    "px-2 py-1 rounded-lg text-xs font-mono flex items-center gap-1 transition-all cursor-pointer",
                    active ? "bg-accent text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
                  )}
                  title={`Preview Viewport: ${dev.id.toUpperCase()} (${dev.label})`}
                >
                  <DevIcon className="w-3.5 h-3.5" />
                  <span className="hidden lg:inline text-[10px]">{dev.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Save, Refresh, Open External, Extend Fullscreen */}
        <div className="flex items-center gap-2">
          {selectedFilePath && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleSave}
              disabled={isSaving}
              className="h-8 text-xs font-mono gap-1.5 border-emerald-500/40 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/15"
            >
              {savedSuccess ? <Check className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
              <span>{savedSuccess ? 'Saved!' : 'Save'}</span>
            </Button>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={() => setRefreshKey((k) => k + 1)}
            className="h-8 text-xs font-mono gap-1"
            title="Reload Live Sandbox"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleOpenInNewTab}
            className="h-8 text-xs font-mono gap-1.5"
            title="Open Preview in New Browser Tab"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Pop Out</span>
          </Button>

          {/* Animated EXTEND / FULLSCREEN Button */}
          <button
            onClick={() => setIsExtendedFullscreen(!isExtendedFullscreen)}
            className={cn(
              "h-8 px-3 rounded-xl text-xs font-mono uppercase tracking-wider font-semibold flex items-center gap-1.5 transition-all duration-300 cursor-pointer shadow-sm",
              isExtendedFullscreen
                ? "bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 shadow-[0_0_20px_rgba(245,158,11,0.4)] scale-105"
                : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-blue-500/20"
            )}
            title={isExtendedFullscreen ? "Exit Extended Cinema View" : "Extend Preview Studio Fullscreen"}
          >
            {isExtendedFullscreen ? (
              <>
                <Minimize2 className="w-3.5 h-3.5" />
                <span>Collapse</span>
              </>
            ) : (
              <>
                <Maximize2 className="w-3.5 h-3.5" />
                <span>Extend</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* MAIN STUDIO BODY */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* COLLAPSIBLE WORKSPACE FILE EXPLORER SIDEBAR */}
        <div
          className={cn(
            "border-r border-border/70 bg-background/60 flex flex-col transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] overflow-hidden shrink-0",
            showFileSidebar ? "w-64 opacity-100" : "w-0 opacity-0 border-r-0"
          )}
        >
          <div className="p-3 border-b border-border/60 flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase tracking-wider font-semibold text-muted-foreground flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-primary" />
              Workspace Files
            </span>
            <button
              onClick={() => loadDirectory(currentDir)}
              className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              title="Refresh Workspace Files"
            >
              <RefreshCw className={cn("w-3.5 h-3.5", loadingFiles && "animate-spin")} />
            </button>
          </div>

          {currentDir && workspaceRoot && currentDir !== workspaceRoot && (
            <button
              onClick={() => {
                const parent = currentDir.replace(/[\\/][^\\/]+$/, '');
                loadDirectory(parent || workspaceRoot);
              }}
              className="px-3 py-2 text-xs font-mono text-primary hover:bg-secondary/60 border-b border-border/40 flex items-center gap-1.5 cursor-pointer text-left"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>.. (Parent Folder)</span>
            </button>
          )}

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {items.map((item) => {
              const isHtml = item.name.toLowerCase().endsWith('.html') || item.name.toLowerCase().endsWith('.htm');
              const isSelected = selectedFilePath === item.path;
              return (
                <button
                  key={item.path}
                  onClick={() => {
                    if (item.is_dir) {
                      loadDirectory(item.path);
                    } else {
                      handleSelectFile(item.path, item.name);
                    }
                  }}
                  className={cn(
                    "w-full px-2.5 py-2 rounded-xl text-xs flex items-center justify-between gap-2 transition-all cursor-pointer text-left",
                    isSelected
                      ? "bg-primary/15 text-primary border border-primary/30 font-semibold"
                      : "text-foreground/85 hover:bg-secondary/60 border border-transparent"
                  )}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {item.is_dir ? (
                      <FolderOpen className="w-4 h-4 text-amber-400 shrink-0" />
                    ) : (
                      <FileCode className={cn("w-4 h-4 shrink-0", isHtml ? "text-emerald-400" : "text-blue-400")} />
                    )}
                    <span className="truncate">{item.name}</span>
                  </div>
                  {isHtml && (
                    <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 shrink-0">
                      HTML
                    </span>
                  )}
                  {item.is_dir && <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />}
                </button>
              );
            })}
          </div>

          <div className="p-2.5 border-t border-border/50 bg-secondary/20">
            <button
              onClick={() => {
                setSelectedFilePath(null);
                setSelectedFileName('starter-preview.html');
                setRawCode(DEFAULT_STARTER_HTML);
                setRenderedSrcDoc(DEFAULT_STARTER_HTML);
              }}
              className="w-full py-1.5 px-3 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 text-xs font-mono flex items-center justify-center gap-1.5 cursor-pointer transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Load Interactive Demo</span>
            </button>
          </div>
        </div>

        {/* SPLIT / CODE / PREVIEW AREA WITH DRAGGABLE DIVIDER */}
        <div ref={splitContainerRef} className="flex-1 flex min-w-0 h-full relative select-none">
          {/* CODE EDITOR PANE */}
          {(viewMode === 'split' || viewMode === 'code') && (
            <div
              style={{ width: viewMode === 'split' ? `${splitRatio}%` : '100%' }}
              className="h-full flex flex-col bg-[#090d16] text-slate-100 border-r border-border/60 transition-[width] duration-75"
            >
              <div className="px-4 py-2 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span className="flex items-center gap-1.5">
                  <Code2 className="w-3.5 h-3.5 text-blue-400" />
                  Live Source Editor ({selectedFileName})
                </span>
                <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                  <Play className="w-2.5 h-2.5 fill-current" /> Instant Hot-Reload
                </span>
              </div>
              <textarea
                value={rawCode}
                onChange={(e) => setRawCode(e.target.value)}
                spellCheck={false}
                className="flex-1 w-full p-4 bg-[#090d16] text-emerald-300 font-mono text-xs leading-relaxed focus:outline-none resize-none selection:bg-blue-500/30"
                placeholder="Paste or write HTML, CSS, and JavaScript here to preview live..."
              />
            </div>
          )}

          {/* DRAGGABLE SPLIT HANDLE */}
          {viewMode === 'split' && (
            <div
              onMouseDown={() => setIsDraggingSplit(true)}
              className={cn(
                "w-3 h-full flex items-center justify-center cursor-col-resize bg-secondary/70 hover:bg-primary/40 border-x border-border/60 transition-colors z-20 group",
                isDraggingSplit && "bg-primary/60"
              )}
              title="Drag left or right to resize Code & Preview panes"
            >
              <GripVertical className="w-3.5 h-3.5 text-muted-foreground group-hover:text-white transition-colors" />
            </div>
          )}

          {/* LIVE IFRAME PREVIEW PANE */}
          {(viewMode === 'split' || viewMode === 'preview') && (
            <div
              style={{ width: viewMode === 'split' ? `${100 - splitRatio}%` : '100%' }}
              className="h-full flex flex-col bg-slate-950/50 items-center justify-center p-3 overflow-auto relative"
            >
              {/* Prevent iframe from stealing mouse events while dragging the split handle */}
              {isDraggingSplit && <div className="absolute inset-0 z-30 cursor-col-resize" />}

              <div
                className={cn(
                  "h-full bg-white rounded-xl overflow-hidden shadow-2xl border border-border/80 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col",
                  viewportWidthClass
                )}
              >
                {/* Simulated Browser Chrome Bar */}
                <div className="h-8 px-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between gap-3 shrink-0">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                  </div>
                  <div className="flex-1 max-w-md px-3 py-0.5 rounded bg-slate-800/90 border border-slate-700 text-[10px] font-mono text-slate-300 truncate text-center">
                    preview://workspace/{selectedFileName}
                  </div>
                  <span className="text-[10px] font-mono text-emerald-400 uppercase">
                    {deviceViewport}
                  </span>
                </div>

                <iframe
                  key={refreshKey}
                  title="Live App Preview Sandbox"
                  srcDoc={renderedSrcDoc}
                  sandbox="allow-scripts allow-modals allow-forms allow-same-origin"
                  className="flex-1 w-full h-full border-0 bg-white"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
