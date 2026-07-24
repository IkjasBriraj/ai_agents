import { useMemo } from 'react';
import { Check, X, FileCode } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface DiffViewerProps {
  filePath: string;
  originalContent: string;
  modifiedContent: string;
  onApply: () => void;
  onReject: () => void;
}

interface DiffLine {
  type: 'added' | 'removed' | 'unchanged';
  content: string;
  lineNumber: number | null;
}

export function AgentModeDiffViewer({ filePath, originalContent, modifiedContent, onApply, onReject }: DiffViewerProps) {
  // Simple line-by-line diff
  const diffLines = useMemo(() => {
    const origLines = originalContent.split('\n');
    const modLines = modifiedContent.split('\n');
    const result: DiffLine[] = [];

    // Very basic comparison: find removed and added blocks
    // This is not a proper Myers diff algorithm, just a simple visualizer for the scope of this task
    let o = 0;
    let m = 0;
    let lineCounter = 1;

    while (o < origLines.length || m < modLines.length) {
      if (o < origLines.length && m < modLines.length && origLines[o] === modLines[m]) {
        result.push({ type: 'unchanged', content: origLines[o], lineNumber: lineCounter });
        o++;
        m++;
        lineCounter++;
      } else {
        // If lines don't match, we assume we remove from original and add from modified
        // In a real app we'd use a diff library like diff, but for here we simplify
        // Let's just output remaining original as removed and remaining modified as added
        const nextMatchInModified = modLines.indexOf(origLines[o], m);
        const nextMatchInOriginal = origLines.indexOf(modLines[m], o);
        
        if (nextMatchInModified !== -1 && (nextMatchInOriginal === -1 || nextMatchInModified - m < nextMatchInOriginal - o)) {
          // Lines were added in modified
          while (m < nextMatchInModified) {
            result.push({ type: 'added', content: modLines[m], lineNumber: null });
            m++;
          }
        } else if (nextMatchInOriginal !== -1) {
          // Lines were removed in original
          while (o < nextMatchInOriginal) {
            result.push({ type: 'removed', content: origLines[o], lineNumber: lineCounter });
            o++;
            lineCounter++;
          }
        } else {
          // Both changed, handle one of each
          if (o < origLines.length) {
            result.push({ type: 'removed', content: origLines[o], lineNumber: lineCounter });
            o++;
            lineCounter++;
          }
          if (m < modLines.length) {
            result.push({ type: 'added', content: modLines[m], lineNumber: null });
            m++;
          }
        }
      }
    }
    return result;
  }, [originalContent, modifiedContent]);

  return (
    <div className="flex flex-col border border-border/50 bg-[#1a1a2e] my-4 overflow-hidden">
      <div className="flex items-center justify-between p-2 bg-[#0d0d1a] border-b border-border/50">
        <div className="flex items-center gap-2 text-sm text-foreground font-mono">
          <FileCode className="w-4 h-4 text-ibm-blue" />
          <span>{filePath}</span>
        </div>
      </div>
      
      <div className="overflow-x-auto max-h-[400px] overflow-y-auto bg-[#0d0d1a] p-2">
        <pre className="font-mono text-[11px] leading-relaxed">
          {diffLines.map((line, idx) => (
            <div 
              key={idx}
              className={cn(
                "px-2 flex w-full",
                line.type === 'added' && "bg-emerald-500/20 text-emerald-300",
                line.type === 'removed' && "bg-red-500/20 text-red-300",
                line.type === 'unchanged' && "text-gray-400"
              )}
            >
              <div className="select-none w-8 text-right pr-3 opacity-50 border-r border-gray-700/50 mr-3">
                {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : line.lineNumber}
              </div>
              <div className="whitespace-pre">{line.content || ' '}</div>
            </div>
          ))}
        </pre>
      </div>
      
      <div className="flex items-center gap-2 p-3 border-t border-border/50 bg-[#151525]">
        <Button 
          size="sm" 
          onClick={onApply}
          className="bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-[10px] uppercase h-8"
        >
          <Check className="w-3.5 h-3.5 mr-1" />
          Apply Changes
        </Button>
        <Button 
          size="sm" 
          variant="outline"
          onClick={onReject}
          className="font-mono text-[10px] uppercase h-8"
        >
          <X className="w-3.5 h-3.5 mr-1" />
          Reject
        </Button>
      </div>
    </div>
  );
}
