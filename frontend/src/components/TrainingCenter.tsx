import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { OllamaService, type Agent } from '@/services/ollama';
import { Database, Lightbulb, Play, Brain, CheckCircle2, Settings } from 'lucide-react';

export const TrainingCenter: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [q, setQ] = useState('');
  const [a, setA] = useState('');
  const [testPrompt, setTestPrompt] = useState('');
  const [testResponse, setTestResponse] = useState('');
  const [isTraining, setIsTraining] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [status, setStatus] = useState<string>('');
  
  const [epochs, setEpochs] = useState(3);
  const [batchSize, setBatchSize] = useState(8);
  const [learningRate, setLearningRate] = useState(0.00002);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    OllamaService.getAgents().then(data => {
      setAgents(data);
      if (data.length > 0) setSelectedAgent(data[0].id);
    });
  }, []);

  const handleTrain = async () => {
    if (!selectedAgent || !q || !a) return;
    setIsTraining(true);
    setStatus('Injecting knowledge...');
    try {
      await OllamaService.trainAgent(selectedAgent, [{ q, a }], { epochs, batch_size: batchSize, learning_rate: learningRate });
      setStatus('Training successful!');
      setQ('');
      setA('');
    } catch (err) {
      setStatus('Training failed.');
    }
    setIsTraining(false);
    setTimeout(() => setStatus(''), 3000);
  };

  const handleTest = async () => {
    if (!selectedAgent || !testPrompt) return;
    setIsTesting(true);
    setTestResponse('');
    try {
      const response = await OllamaService.chat(selectedAgent, testPrompt);
      setTestResponse(response);
    } catch (err) {
      setTestResponse('Error connecting to agent.');
    }
    setIsTesting(false);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 max-w-7xl mx-auto">
      {/* Train Section */}
      <Card className="border-t-4 border-ibm-blue shadow-lg">
        <CardHeader className="pb-8">
          <CardTitle className="flex items-center gap-3 text-3xl font-light">
            <Brain className="w-8 h-8 text-ibm-blue" />
            Knowledge Training
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-8">
          <div className="bg-ibm-blue/5 border-l-4 border-ibm-blue p-6 rounded-r-lg flex items-start gap-4 text-lg text-muted-foreground">
            <Lightbulb className="w-6 h-6 flex-shrink-0 text-ibm-blue mt-1" />
            <span className="leading-relaxed">Teach your agent new facts by providing examples of Questions and ideal Answers. Keep it simple and clear.</span>
          </div>

          <div className="space-y-3">
            <label className="text-lg font-medium text-foreground/80">Select Agent to Train</label>
            <select
              className="w-full p-5 bg-background border-2 border-muted focus:border-ibm-blue rounded-xl text-lg outline-none transition-colors appearance-none cursor-pointer"
              value={selectedAgent}
              onChange={e => setSelectedAgent(e.target.value)}
            >
              {agents.map(agent => (
                <option key={agent.id} value={agent.id}>{agent.name} ({agent.base_model})</option>
              ))}
            </select>
          </div>

          <div className="space-y-6 bg-muted/20 p-8 rounded-2xl border border-border/50">
            <div className="space-y-3">
              <label className="text-lg font-medium text-foreground/80">Sample Question (User says...)</label>
              <input
                className="w-full p-5 bg-background border-2 border-muted focus:border-ibm-blue rounded-xl text-lg outline-none transition-colors placeholder:text-muted-foreground/50"
                placeholder="e.g. How do I reset my password?"
                value={q}
                onChange={e => setQ(e.target.value)}
              />
            </div>
            <div className="space-y-3">
              <label className="text-lg font-medium text-foreground/80">Ideal Answer (Agent replies...)</label>
              <textarea
                className="w-full p-5 bg-background border-2 border-muted focus:border-ibm-blue rounded-xl text-lg outline-none transition-colors placeholder:text-muted-foreground/50 min-h-[150px] resize-y"
                placeholder="e.g. Go to settings and click 'Security'..."
                value={a}
                onChange={e => setA(e.target.value)}
              />
            </div>

            {/* Advanced Settings */}
            <div className="pt-4 border-t border-border/50">
              <button 
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 text-md font-medium text-muted-foreground hover:text-ibm-blue transition-colors"
              >
                <Settings className="w-5 h-5" />
                {showAdvanced ? 'Hide Hyperparameters' : 'Configure Hyperparameters (Epochs, Batch Size)'}
              </button>
              
              {showAdvanced && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6 animate-in fade-in slide-in-from-top-2">
                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Epochs</label>
                    <input
                      type="number"
                      className="w-full p-4 bg-background border-2 border-muted focus:border-ibm-blue rounded-xl text-lg outline-none transition-colors"
                      value={epochs}
                      onChange={e => setEpochs(Number(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Batch Size</label>
                    <input
                      type="number"
                      className="w-full p-4 bg-background border-2 border-muted focus:border-ibm-blue rounded-xl text-lg outline-none transition-colors"
                      value={batchSize}
                      onChange={e => setBatchSize(Number(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Learning Rate</label>
                    <input
                      type="number"
                      step="0.00001"
                      className="w-full p-4 bg-background border-2 border-muted focus:border-ibm-blue rounded-xl text-lg outline-none transition-colors"
                      value={learningRate}
                      onChange={e => setLearningRate(Number(e.target.value))}
                    />
                  </div>
                </div>
              )}
            </div>
            
            <Button 
              className="w-full h-auto py-5 text-xl font-medium rounded-xl mt-4" 
              onClick={handleTrain}
              disabled={isTraining || !q || !a || !selectedAgent}
            >
              <Database className="w-6 h-6 mr-3" />
              {isTraining ? 'Training...' : 'Inject Knowledge'}
            </Button>
            
            {status && (
              <div className="flex items-center gap-3 text-lg text-green-600 justify-center font-medium animate-in fade-in slide-in-from-bottom-2">
                <CheckCircle2 className="w-6 h-6" /> {status}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Test Section */}
      <Card className="border-t-4 border-muted shadow-lg bg-muted/5 border-x-0 border-b-0">
        <CardHeader className="pb-8">
          <CardTitle className="flex items-center gap-3 text-3xl font-light text-foreground/80">
            <Play className="w-8 h-8 text-muted-foreground" />
            Live Testing
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-8">
          <div className="bg-background border border-border p-6 rounded-lg flex items-start gap-4 text-lg text-muted-foreground shadow-sm">
            <Lightbulb className="w-6 h-6 flex-shrink-0 mt-1 opacity-70" />
            <span className="leading-relaxed">Test your agent immediately to see if it learned the new knowledge you provided.</span>
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <label className="text-lg font-medium text-foreground/80">Test Prompt</label>
              <input
                className="w-full p-6 bg-background border-2 border-ibm-blue/30 focus:border-ibm-blue shadow-inner rounded-xl text-xl outline-none transition-all placeholder:text-muted-foreground/40"
                placeholder="Ask your agent something..."
                value={testPrompt}
                onChange={e => setTestPrompt(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleTest()}
              />
            </div>
            
            <Button 
              variant="outline"
              className="w-full h-auto py-5 text-xl font-medium rounded-xl border-2 hover:bg-ibm-blue hover:text-white transition-colors" 
              onClick={handleTest}
              disabled={isTesting || !testPrompt || !selectedAgent}
            >
              {isTesting ? 'Generating Response...' : 'Send Test'}
            </Button>

            {testResponse && (
              <div className="mt-8 p-8 bg-background border border-border/60 shadow-lg rounded-2xl text-xl leading-relaxed whitespace-pre-wrap min-h-[250px] animate-in fade-in slide-in-from-bottom-4">
                <div className="text-sm text-ibm-blue mb-4 font-mono uppercase tracking-widest flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-ibm-blue animate-pulse"></div>
                  Agent Response
                </div>
                {testResponse}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
