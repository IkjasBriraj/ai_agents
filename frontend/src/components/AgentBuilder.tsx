import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { User, Settings, Shield, Plus, Lightbulb } from 'lucide-react';
import { OllamaService, type Agent } from '@/services/ollama';

interface BuilderProps {
  onAgentCreated: () => void;
}

export const AgentBuilder: React.FC<BuilderProps> = ({ onAgentCreated }) => {
  const [step, setStep] = useState(1);
  const [availableModels, setAvailableModels] = useState<string[]>([
    'qwen3.5:9b', 'gemma4:31b-cloud', 'granite4.1:8b', 'llama3', 'mistral'
  ]);
  const [formData, setFormData] = useState<Partial<Agent>>({
    name: '',
    persona: '',
    system_prompt: '',
    base_model: 'qwen3.5:9b',
    tools: []
  });

  useEffect(() => {
    OllamaService.getModels().then(models => {
      if (models && models.length > 0) {
        const modelNames = models.map(m => m.name);
        // Ensure some requested models are always an option even if not pulled yet
        const combined = Array.from(new Set([...modelNames, 'granite4.1:8b', 'llama3']));
        setAvailableModels(combined);
        if (!combined.includes(formData.base_model as string)) {
          setFormData(prev => ({ ...prev, base_model: combined[0] }));
        }
      }
    });
  }, []);

  const nextStep = () => setStep(s => s + 1);
  const prevStep = () => setStep(s => s - 1);

  const handleSubmit = async () => {
    const id = Math.random().toString(36).substring(7);
    await OllamaService.createAgent({ ...formData, id } as Agent);
    setStep(1);
    setFormData({ name: '', persona: '', system_prompt: '', base_model: availableModels[0] || 'qwen3.5:9b', tools: [] });
    onAgentCreated();
  };

  return (
    <Card className="max-w-2xl mx-auto border-ibm-blue border-t-4">
      <CardHeader>
        <div className="flex justify-between items-center mb-4">
          <span className="text-xs font-mono text-ibm-blue font-bold tracking-widest uppercase">
            Step {step} of 3
          </span>
          <div className="flex gap-2">
            {[1, 2, 3].map(s => (
              <div key={s} className={`h-1 w-8 ${s <= step ? 'bg-ibm-blue' : 'bg-muted'}`} />
            ))}
          </div>
        </div>
        <CardTitle className="text-3xl">
          {step === 1 && "Identity"}
          {step === 2 && "Knowledge & Logic"}
          {step === 3 && "Capabilities"}
        </CardTitle>
      </CardHeader>
      
      <CardContent className="min-h-[300px]">
        {step === 1 && (
          <div className="space-y-6 animate-in fade-in">
            <div className="bg-ibm-blue/10 text-ibm-blue p-3 rounded flex items-start gap-2 text-sm mb-4">
              <Lightbulb className="w-5 h-5 flex-shrink-0" />
              <span>Give your agent a clear name and pick an AI model. For quick tasks, try Mistral. For smart logic, try Llama 3 or Granite.</span>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <User className="w-4 h-4" /> Agent Name
              </label>
              <input
                className="w-full p-4 bg-muted border border-border focus:ring-1 focus:ring-ibm-blue outline-none"
                placeholder="e.g. Health Companion"
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Settings className="w-4 h-4" /> Base Model
              </label>
              <select
                className="w-full p-4 bg-muted border border-border focus:ring-1 focus:ring-ibm-blue outline-none"
                value={formData.base_model}
                onChange={e => setFormData({...formData, base_model: e.target.value})}
              >
                {availableModels.map(model => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6 animate-in fade-in">
            <div className="bg-ibm-blue/10 text-ibm-blue p-3 rounded flex items-start gap-2 text-sm mb-4">
              <Lightbulb className="w-5 h-5 flex-shrink-0" />
              <span>Describe who the agent is and how it should behave. Keep instructions clear and simple.</span>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Shield className="w-4 h-4" /> Persona Description
              </label>
              <input
                className="w-full p-4 bg-muted border border-border focus:ring-1 focus:ring-ibm-blue outline-none"
                placeholder="e.g. A calm, helpful assistant for seniors..."
                value={formData.persona}
                onChange={e => setFormData({...formData, persona: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">System Prompt (Instructions)</label>
              <textarea
                className="w-full p-4 bg-muted border border-border focus:ring-1 focus:ring-ibm-blue outline-none min-h-[150px]"
                placeholder="Talk slowly, use simple terms, and always prioritize safety..."
                value={formData.system_prompt}
                onChange={e => setFormData({...formData, system_prompt: e.target.value})}
              />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-6 animate-in fade-in">
            <p className="text-sm text-muted-foreground">Select tools this agent can use:</p>
            <div className="grid grid-cols-2 gap-4">
              {['Web Search', 'Health Database', 'Calculator', 'Smart Home', 'Medication Alerts'].map(tool => (
                <label key={tool} className="flex items-center gap-3 p-4 bg-muted border border-border cursor-pointer hover:bg-muted/80">
                  <input
                    type="checkbox"
                    className="w-5 h-5 accent-ibm-blue"
                    checked={formData.tools?.includes(tool)}
                    onChange={e => {
                      const newTools = e.target.checked 
                        ? [...(formData.tools || []), tool]
                        : (formData.tools || []).filter(t => t !== tool);
                      setFormData({...formData, tools: newTools});
                    }}
                  />
                  <span>{tool}</span>
                </label>
              ))}
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex justify-between border-t border-border pt-6">
        <Button variant="ghost" onClick={prevStep} disabled={step === 1}>
          Back
        </Button>
        {step < 3 ? (
          <Button onClick={nextStep} disabled={step === 1 && !formData.name}>
            Continue
          </Button>
        ) : (
          <Button variant="carbon" onClick={handleSubmit}>
            <Plus className="mr-2" /> Create Agent
          </Button>
        )}
      </CardFooter>
    </Card>
  );
};
