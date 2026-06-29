import React, { useState, useEffect } from 'react';
import { OllamaService } from '@/services/ollama';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Folder, 
  File, 
  ChevronLeft, 
  HardDrive, 
  FileCode, 
  RefreshCw, 
  ShieldAlert, 
  Info,
  Plus,
  Edit2,
  Save,
  X
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface WorkspaceItem {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
}

export const WorkspaceExplorer: React.FC = () => {
  const [roots, setRoots] = useState<{ workspace: string; allowed_paths: string[] } | null>(null);
  const [currentPath, setCurrentPath] = useState<string>('');
  const [items, setItems] = useState<WorkspaceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Selected file details
  const [selectedFile, setSelectedFile] = useState<{ path: string; name: string } | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [loadingFile, setLoadingFile] = useState<boolean>(false);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [localContent, setLocalContent] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);

  const handleSaveFile = async () => {
    if (!selectedFile) return;
    setIsSaving(true);
    try {
      await OllamaService.writeWorkspaceFile(selectedFile.path, localContent);
      setFileContent(localContent);
      setIsEditing(false);
    } catch (err: any) {
      console.error("Failed to save file:", err);
      alert(err?.response?.data?.detail || "Could not save file. Make sure you have permission.");
    } finally {
      setIsSaving(false);
    }
  };

  // Folder creation states
  const [newDirName, setNewDirName] = useState('');
  const [showAddDir, setShowAddDir] = useState(false);

  const handleCreateDir = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDirName.trim()) return;
    try {
      await OllamaService.createWorkspaceDirectory(currentPath, newDirName.trim());
      setNewDirName('');
      setShowAddDir(false);
      fetchDirList(currentPath);
    } catch (err: any) {
      console.error("Failed to create directory:", err);
      alert(err?.response?.data?.detail || "Could not create directory. Make sure you have permission.");
    }
  };

  // Fetch roots
  const fetchRoots = async () => {
    try {
      const response = await OllamaService.getWorkspaceRoots();
      if (response && response.status === 'success') {
        setRoots({
          workspace: response.workspace,
          allowed_paths: response.allowed_paths
        });
        // Default to workspace root if not set
        if (!currentPath) {
          setCurrentPath(response.workspace);
        }
      }
    } catch (err) {
      console.error("Failed to fetch roots", err);
      setError("Failed to fetch workspace root directory settings.");
    }
  };

  // Fetch directory list
  const fetchDirList = async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await OllamaService.getWorkspaceList(path);
      if (response && response.status === 'success') {
        setCurrentPath(response.path);
        // Sort items: folders first, then files alphabetically
        const sortedItems = [...response.items].sort((a, b) => {
          if (a.is_dir && !b.is_dir) return -1;
          if (!a.is_dir && b.is_dir) return 1;
          return a.name.localeCompare(b.name);
        });
        setItems(sortedItems);
      }
    } catch (err: any) {
      console.error("Failed to fetch directory items", err);
      setError(err?.response?.data?.detail || "Access denied or folder not found.");
    } finally {
      setLoading(false);
    }
  };

  // Fetch file contents
  const fetchFile = async (filePath: string, fileName: string) => {
    setLoadingFile(true);
    try {
      const response = await OllamaService.getWorkspaceFile(filePath);
      if (response && response.status === 'success') {
        setSelectedFile({ path: filePath, name: fileName });
        setFileContent(response.content);
        setLocalContent(response.content || '');
        setIsEditing(false);
      }
    } catch (err: any) {
      console.error("Failed to load file contents", err);
      alert(err?.response?.data?.detail || "Could not read file. Make sure you have permission.");
    } finally {
      setLoadingFile(false);
    }
  };

  useEffect(() => {
    fetchRoots();
  }, []);

  useEffect(() => {
    if (currentPath) {
      fetchDirList(currentPath);
    }
  }, [currentPath]);

  // Navigate back to parent folder
  const handleGoBack = () => {
    // Basic parent directory computation
    const separator = currentPath.includes('/') ? '/' : '\\';
    const parts = currentPath.split(separator);
    if (parts.length > 1) {
      parts.pop();
      const parent = parts.join(separator);
      // Ensure we don't go past the root levels or check if the parent matches any whitelisted paths
      if (parent) {
        setCurrentPath(parent);
      }
    }
  };

  // Check if we are at one of the roots (cannot navigate back further)
  const isAtRoot = () => {
    if (!roots) return true;
    const cleanCurrent = currentPath.replace(/\\/g, '/').toLowerCase();
    const cleanWorkspace = roots.workspace.replace(/\\/g, '/').toLowerCase();
    const cleanAllowed = roots.allowed_paths.map(p => p.replace(/\\/g, '/').toLowerCase());
    
    return cleanCurrent === cleanWorkspace || cleanAllowed.includes(cleanCurrent);
  };

  const getFormatSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500 pb-20">
      
      {/* Roots Selector Header */}
      <div className="flex flex-wrap gap-3 items-center justify-between border-b border-border/30 pb-4">
        <div className="flex flex-wrap gap-2">
          {roots && (
            <>
              {/* Main default website root */}
              <button
                onClick={() => setCurrentPath(roots.workspace)}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 border font-mono text-xs uppercase tracking-wider transition-all",
                  currentPath.replace(/\\/g, '/').toLowerCase().startsWith(roots.workspace.replace(/\\/g, '/').toLowerCase())
                    ? "bg-ibm-blue border-ibm-blue text-white"
                    : "bg-muted/30 border-border/50 text-muted-foreground hover:bg-muted"
                )}
              >
                <HardDrive className="w-3.5 h-3.5" />
                Default Workspace
              </button>
              
              {/* Whitelisted allowed external paths */}
              {roots.allowed_paths.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentPath(p)}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 border font-mono text-xs uppercase tracking-wider transition-all",
                    currentPath.replace(/\\/g, '/').toLowerCase().startsWith(p.replace(/\\/g, '/').toLowerCase())
                      ? "bg-accent border-accent text-white"
                      : "bg-muted/30 border-border/50 text-muted-foreground hover:bg-muted"
                  )}
                >
                  <Folder className="w-3.5 h-3.5" />
                  Allowed Path {idx + 1}
                </button>
              ))}
            </>
          )}
        </div>
        <div className="flex gap-2 items-center">
          {showAddDir ? (
            <form onSubmit={handleCreateDir} className="flex gap-2 items-center animate-in slide-in-from-right-2 duration-200">
              <input
                type="text"
                required
                placeholder="New folder name..."
                className="px-3 py-1.5 text-xs bg-background border border-border rounded outline-none focus:border-ibm-blue font-sans h-9"
                value={newDirName}
                onChange={e => setNewDirName(e.target.value)}
              />
              <Button type="submit" size="sm" className="h-9 text-[10px] uppercase">
                Create
              </Button>
              <Button 
                type="button" 
                size="sm" 
                variant="outline" 
                onClick={() => { setShowAddDir(false); setNewDirName(''); }}
                className="h-9 text-[10px] uppercase"
              >
                Cancel
              </Button>
            </form>
          ) : (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowAddDir(true)}
              className="h-9 font-mono text-[10px] uppercase gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Directory
            </Button>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={() => fetchDirList(currentPath)}
            className="h-9 font-mono text-[10px] uppercase gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh Files
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: Directory Explorer Tree */}
        <div className="lg:col-span-4 space-y-4">
          <Card className="carbon-card min-h-[500px]">
            <CardHeader className="pb-3 border-b border-border/30 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-semibold tracking-wider font-mono text-muted-foreground uppercase">
                Directory Browser
              </CardTitle>
              <span className="text-[9px] font-mono bg-muted px-1.5 py-0.5 border">
                FILE SYSTEM
              </span>
            </CardHeader>
            <CardContent className="pt-4">
              
              {/* Current Breadcrumb Location */}
              <div className="flex items-center gap-2.5 pb-3 border-b border-border/30 mb-3">
                {!isAtRoot() && (
                  <button 
                    onClick={handleGoBack}
                    className="p-1 hover:bg-muted border border-border/40 text-muted-foreground hover:text-foreground transition-all shrink-0"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                )}
                <div className="font-mono text-[10px] text-muted-foreground truncate select-all" title={currentPath}>
                  {currentPath}
                </div>
              </div>

              {/* Loader */}
              {loading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3">
                  <RefreshCw className="w-6 h-6 animate-spin text-ibm-blue" />
                  <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">Reading Path...</span>
                </div>
              ) : error ? (
                <div className="border border-destructive/20 bg-destructive/5 p-4 text-center space-y-2">
                  <ShieldAlert className="w-8 h-8 text-destructive mx-auto" />
                  <div className="font-bold text-xs uppercase text-destructive-foreground tracking-wider font-mono">Access Denied</div>
                  <p className="text-xs text-muted-foreground font-light leading-relaxed">{error}</p>
                </div>
              ) : items.length === 0 ? (
                <div className="text-center py-20 border border-dashed border-border">
                  <Info className="w-8 h-8 text-muted-foreground opacity-50 mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground font-mono">This directory is empty</p>
                </div>
              ) : (
                <div className="space-y-1 max-h-[500px] overflow-y-auto pr-1">
                  {items.map((item, idx) => {
                    const isSelected = selectedFile?.path === item.path;
                    return (
                      <button
                        key={idx}
                        onClick={() => {
                          if (item.is_dir) {
                            setCurrentPath(item.path);
                          } else {
                            fetchFile(item.path, item.name);
                          }
                        }}
                        className={cn(
                          "w-full flex items-center justify-between p-2.5 border text-left transition-all duration-200 group text-xs",
                          isSelected
                            ? "border-accent/40 bg-accent/5 text-foreground"
                            : "border-transparent bg-transparent hover:bg-muted/40 hover:border-border/30 text-muted-foreground hover:text-foreground"
                        )}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          {item.is_dir ? (
                            <Folder className="w-4 h-4 text-ibm-blue shrink-0" />
                          ) : (
                            <File className="w-4 h-4 text-muted-foreground group-hover:text-primary shrink-0" />
                          )}
                          <span className="truncate font-sans font-medium">{item.name}</span>
                        </div>
                        {!item.is_dir && (
                          <span className="font-mono text-[9px] text-muted-foreground/60 shrink-0 group-hover:text-muted-foreground">
                            {getFormatSize(item.size)}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}

            </CardContent>
          </Card>
        </div>

        {/* Right Side: File Reader Viewer */}
        <div className="lg:col-span-8">
          <Card className="carbon-card min-h-[500px] flex flex-col">
            <CardHeader className="pb-3 border-b border-border/30 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-xs font-semibold tracking-wider font-mono text-muted-foreground uppercase flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-accent" />
                  File Inspector
                </CardTitle>
                {selectedFile && (
                  <p className="text-[10px] text-muted-foreground font-mono mt-1 select-all">
                    {selectedFile.path}
                  </p>
                )}
              </div>
              {selectedFile && (
                <span className="text-[9px] font-mono bg-accent/10 border border-accent/20 px-2 py-0.5 text-accent uppercase">
                  {selectedFile.name.split('.').pop() || 'Text'}
                </span>
              )}
            </CardHeader>
            <CardContent className="flex-1 flex flex-col pt-4 min-h-[400px]">
            {loadingFile ? (
                <div className="flex-1 flex flex-col items-center justify-center gap-3">
                  <RefreshCw className="w-8 h-8 animate-spin text-accent" />
                  <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">Loading Contents...</span>
                </div>
              ) : selectedFile && fileContent !== null ? (
                <div className="flex-1 flex flex-col">
                  {/* Toolbar */}
                  <div className="flex gap-2 justify-end mb-3">
                    {isEditing ? (
                      <>
                        <Button
                          size="sm"
                          onClick={handleSaveFile}
                          disabled={isSaving}
                          className="h-8 font-mono text-[10px] uppercase gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                        >
                          {isSaving ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : (
                            <Save className="w-3 h-3" />
                          )}
                          Save Changes
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setLocalContent(fileContent || '');
                            setIsEditing(false);
                          }}
                          disabled={isSaving}
                          className="h-8 font-mono text-[10px] uppercase gap-1"
                        >
                          <X className="w-3 h-3" />
                          Cancel
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setIsEditing(true)}
                        className="h-8 font-mono text-[10px] uppercase gap-1"
                      >
                        <Edit2 className="w-3 h-3" />
                        Edit Code
                      </Button>
                    )}
                  </div>

                  {/* File Reader container with Code aesthetics */}
                  <div className="flex-1 border border-border/60 font-mono text-sm overflow-hidden flex flex-col min-h-[450px]">
                    {isEditing ? (
                      <textarea
                        className="flex-1 w-full p-4 bg-black/50 text-foreground outline-none resize-none font-mono text-sm leading-relaxed border-0 focus:ring-0 focus:outline-none"
                        value={localContent}
                        onChange={e => setLocalContent(e.target.value)}
                        placeholder="Write your code here..."
                      />
                    ) : (
                      <div className="flex-1 bg-black/40 p-4 overflow-auto max-h-[550px] leading-relaxed selection:bg-accent selection:text-white">
                        <pre className="text-foreground whitespace-pre-wrap select-text">
                          {fileContent || <span className="text-muted-foreground/50 italic">(File is empty)</span>}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col justify-center items-center text-center opacity-70 p-12">
                  <div className="p-4 border border-dashed rounded-none border-border mb-4">
                    <FileCode className="w-10 h-10 text-muted-foreground/80" />
                  </div>
                  <h4 className="font-semibold text-sm uppercase tracking-wider font-mono text-muted-foreground">No File Inspected</h4>
                  <p className="text-xs text-muted-foreground max-w-xs mt-1.5 font-light">
                    Select any file from the directory explorer in the left panel to inspect its syntax and content.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

      </div>

    </div>
  );
};
