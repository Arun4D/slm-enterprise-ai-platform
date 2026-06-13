import { useEffect, useMemo, useState, useRef, type ChangeEvent } from 'react';

const sections = [
  { id: 'chat', label: 'Conversational Assistant' },
  { id: 'logs', label: 'Deep Log Analysis' },
  { id: 'snow', label: 'ServiceNow Ticketing' },
  { id: 'marketplace', label: 'Agent Marketplace' },
  { id: 'settings', label: 'Config & Tuning' },
  { id: 'admin', label: 'Admin Controls' }
] as const;

type Section = (typeof sections)[number]['id'];

type Message = {
  role: 'user' | 'assistant' | 'system';
  text: string;
  logResult?: LogAnalysisResult;
  agent_id?: string;
};

type Agent = {
  id: string;
  name: string;
  version?: string;
  status?: string;
  capabilities?: string[];
  enabled?: boolean;
};

type Plugin = {
  name: string;
  version: string;
  description: string;
  capabilities?: string[];
};

type LogPattern = {
  pattern: string;
  count: number;
  level?: string;
  samples?: string[];
  remediation?: string;
};

type LogAnalysisResult = {
  query_answer?: string | null;
  files_analyzed?: number;
  total_entries?: number;
  classifier_version?: string;
  application_status?: {
    application_started?: boolean;
    application_name?: string | null;
    pid?: number | null;
    port?: number | null;
    startup_seconds?: number | null;
    jvm_running_seconds?: number | null;
    evidence?: string[];
  };
  classified_entries?: {
    errors?: unknown[];
    warnings?: unknown[];
    info?: unknown[];
  };
  patterns?: LogPattern[];
  errors?: Array<{ file?: string; error?: string }>;
  summary?: string;
};

const initialMessages: Message[] = [
  {
    role: 'system',
    text: 'You are the SLM Enterprise Assistant. Type your request or select a specialized agent below. I can scan directories, troubleshoot infrastructure failures, and audit ITSM logs.'
  }
];

const fallbackAgents: Agent[] = [
  { id: 'auto', name: '⚡ Auto Router (SLM)' },
  { id: 'log_analysis_agent', name: '📁 Log Analysis Agent' },
  { id: 'servicenow_agent', name: '🎫 ServiceNow Agent' },
  { id: 'github_actions_agent', name: '⚙️ GitHub Actions Agent' },
  { id: 'terraform_agent', name: '🛠️ Terraform Agent' },
  { id: 'ansible_agent', name: '⚡ Ansible Agent' }
];

const fileEnabledAgents = new Set([
  'log_analysis_agent',
  'github_actions_agent',
  'terraform_agent',
  'ansible_agent'
]);

function LogAnalysisCard({ result, compact = false, theme = 'dark' }: { result: LogAnalysisResult; compact?: boolean; theme?: 'light' | 'dark' }) {
  const classified = result.classified_entries ?? {};
  const errorCount = classified.errors?.length ?? 0;
  const warningCount = classified.warnings?.length ?? 0;
  const infoCount = classified.info?.length ?? 0;
  const patterns = result.patterns ?? [];
  const appStatus = result.application_status;
  const isClean = errorCount === 0 && warningCount === 0;

  return (
    <div className={`${compact ? 'mt-2' : 'mt-4'} overflow-hidden rounded-2xl border transition-all duration-300 shadow-lg backdrop-blur-md ${theme === 'dark' ? 'border-slate-800 bg-slate-950/80 text-slate-100' : 'border-slate-200 bg-white text-slate-800'}`}>
      <div className={`border-b px-5 py-4 transition-all duration-300 ${theme === 'dark' ? 'border-slate-800 bg-slate-900/60' : 'border-slate-100 bg-slate-50/50'}`}>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className={`text-[10px] font-bold uppercase tracking-[0.2em] ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>Log Diagnostic Report</p>
            <h3 className={`mt-1 text-md font-semibold ${theme === 'dark' ? 'text-slate-100' : 'text-slate-900'}`}>
              {result.query_answer ?? (isClean ? 'System Integrity Validated (Clean)' : `${errorCount} errors and ${warningCount} warnings parsed`)}
            </h3>
          </div>
          <span className={`w-fit rounded-full px-3 py-0.5 text-xs font-semibold ${isClean ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
            {isClean ? 'Healthy' : 'Investigate'}
          </span>
        </div>
      </div>

      <div className="space-y-4 p-4">
        <div className="grid gap-2 grid-cols-5 text-center">
          {[
            ['Files', result.files_analyzed ?? 0],
            ['Total lines', result.total_entries ?? 0],
            ['Errors', errorCount],
            ['Warnings', warningCount],
            ['Info', infoCount]
          ].map(([label, value]) => (
            <div key={label} className={`rounded-xl border transition p-2 ${theme === 'dark' ? 'border-slate-800/80 bg-slate-900/40' : 'border-slate-200 bg-slate-50'}`}>
              <p className={`text-[9px] uppercase tracking-wider ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>{label}</p>
              <p className={`mt-1 text-lg font-bold ${theme === 'dark' ? 'text-slate-100' : 'text-slate-900'}`}>{value}</p>
            </div>
          ))}
        </div>

        {appStatus && (
          <div className={`rounded-xl border transition p-3 ${theme === 'dark' ? 'border-slate-800 bg-slate-900/50' : 'border-slate-200 bg-slate-100/50'}`}>
            <p className={`text-xs font-semibold ${theme === 'dark' ? 'text-slate-200' : 'text-slate-800'}`}>
              {appStatus.application_started ? '🚀 Lifecycle Event: Successful startup detected' : '⚠️ Lifecycle Event: Incomplete boot parsed'}
            </p>
            <p className={`mt-1 text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>
              {appStatus.application_name ?? 'Application'}
              {appStatus.startup_seconds != null ? ` completed boot in ${appStatus.startup_seconds}s` : ''}
              {appStatus.port != null ? ` listening on port ${appStatus.port}` : ''}
              {appStatus.pid != null ? ` (PID ${appStatus.pid})` : ''}
            </p>
          </div>
        )}

        {patterns.length > 0 ? (
          <div className="space-y-2">
            <p className={`text-xs font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}`}>Actionable Event Signatures</p>
            <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
              {patterns.slice(0, 4).map((pattern, idx) => (
                <div key={idx} className={`rounded-lg border transition p-2.5 ${theme === 'dark' ? 'border-slate-800/80 bg-slate-950' : 'border-slate-200 bg-slate-50'}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${pattern.level === 'ERROR' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>
                      {pattern.level ?? 'ISSUE'}
                    </span>
                    <span className={`text-[10px] ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>{pattern.count} times</span>
                  </div>
                  <p className={`mt-1.5 font-mono text-[11px] leading-4 break-all ${theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}`}>
                    {pattern.samples && pattern.samples.length > 0 ? pattern.samples[0] : pattern.pattern}
                  </p>
                  {pattern.remediation && (
                    <div className={`mt-2.5 rounded-xl border p-2 text-[10px] leading-4 flex items-start gap-1.5 transition-all duration-200 ${theme === 'dark' ? 'border-lime-500/15 bg-lime-500/5 text-lime-400' : 'border-emerald-500/25 bg-emerald-50/50 text-emerald-700 font-medium'}`}>
                      <span className="shrink-0 text-xs">💡</span>
                      <div>
                        <span className="font-bold uppercase tracking-wider text-[9px] mr-1">Remediation:</span>
                        {pattern.remediation}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className={`rounded-xl border p-3 text-xs ${theme === 'dark' ? 'border-emerald-500/10 bg-emerald-500/5 text-emerald-400' : 'border-emerald-500/20 bg-emerald-50 text-emerald-700'}`}>
            ✓ Log analyzer found zero signature issues matching platform exception rules.
          </div>
        )}
      </div>
    </div>
  );
}

function RichText({ text, theme = 'dark' }: { text: string; theme?: 'light' | 'dark' }) {
  const lines = text.split('\n');
  const blocks: Array<
    | { type: 'code'; language: string; content: string }
    | { type: 'table'; rows: string[][] }
    | { type: 'line'; line: string; index: number }
  > = [];

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();

    if (trimmed.startsWith('```')) {
      const language = trimmed.replace(/^```/, '').trim() || 'code';
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        codeLines.push(lines[index]);
        index += 1;
      }
      blocks.push({ type: 'code', language, content: codeLines.join('\n') });
      continue;
    }

    if (/^\|.*\|$/.test(trimmed)) {
      const tableLines: string[] = [];
      while (index < lines.length && /^\|.*\|$/.test(lines[index].trim())) {
        if (!lines[index].includes('---')) tableLines.push(lines[index]);
        index += 1;
      }
      index -= 1;
      const rows = tableLines.map((tableLine) =>
        tableLine
          .split('|')
          .map((cell) => cell.trim().replace(/\*\*/g, '').replace(/`/g, ''))
          .filter(Boolean)
      );
      blocks.push({ type: 'table', rows });
      continue;
    }

    blocks.push({ type: 'line', line, index });
  }

  return (
    <div className={`space-y-2.5 leading-6 transition-colors ${theme === 'dark' ? 'text-slate-200' : 'text-slate-800'}`}>
      {blocks.map((block, blockIndex) => {
        if (block.type === 'code') {
          return (
            <div
              key={`code-${blockIndex}`}
              className={`overflow-hidden rounded-xl border text-left shadow-sm ${theme === 'dark' ? 'border-slate-800 bg-slate-950' : 'border-slate-200 bg-slate-950'}`}
            >
              <div className={`flex items-center justify-between border-b px-4 py-2 ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-400' : 'border-slate-800 bg-slate-900 text-slate-300'}`}>
                <span className="text-[10px] font-bold uppercase tracking-wider">{block.language}</span>
              </div>
              <pre className="max-w-full overflow-x-auto p-4 text-[12px] leading-5 text-slate-100">
                <code className="font-mono whitespace-pre">{block.content}</code>
              </pre>
            </div>
          );
        }

        if (block.type === 'table') {
          const [header, ...body] = block.rows;
          return (
            <div key={`table-${blockIndex}`} className={`overflow-x-auto rounded-xl border ${theme === 'dark' ? 'border-slate-800' : 'border-slate-200'}`}>
              <table className="w-full border-collapse text-left text-xs">
                {header && (
                  <thead className={theme === 'dark' ? 'bg-slate-900 text-slate-300' : 'bg-slate-100 text-slate-700'}>
                    <tr>
                      {header.map((cell, cellIndex) => (
                        <th key={cellIndex} className="border-b px-3 py-2 font-semibold">{cell}</th>
                      ))}
                    </tr>
                  </thead>
                )}
                <tbody className={theme === 'dark' ? 'bg-slate-950/40 text-slate-300' : 'bg-white text-slate-700'}>
                  {body.map((row, rowIndex) => (
                    <tr key={rowIndex} className={theme === 'dark' ? 'border-t border-slate-800' : 'border-t border-slate-100'}>
                      {row.map((cell, cellIndex) => (
                        <td key={cellIndex} className="px-3 py-2 align-top font-mono text-[11px]">{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        const { line, index } = block;
        const trimmed = line.trim();
        if (!trimmed) return <div key={index} className="h-1" />;
        
        if (trimmed.startsWith('### ')) {
          return (
            <h4 key={index} className={`pt-2 text-md font-bold border-b pb-1 ${theme === 'dark' ? 'text-slate-100 border-slate-800/80' : 'text-slate-900 border-slate-200'}`}>
              {trimmed.replace(/^###\s+/, '')}
            </h4>
          );
        }
        if (trimmed.startsWith('## ')) {
          return (
            <h3 key={index} className={`text-lg font-bold border-b pb-1 pt-3 ${theme === 'dark' ? 'text-slate-100 border-slate-700/50' : 'text-slate-900 border-slate-200'}`}>
              {trimmed.replace(/^##\s+/, '')}
            </h3>
          );
        }
        if (trimmed.startsWith('#### ')) {
          return <h5 key={index} className={`text-sm font-semibold ${theme === 'dark' ? 'text-slate-200' : 'text-slate-800'}`}>{trimmed.replace(/^####\s+/, '')}</h5>;
        }
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          return <p key={index} className={`pl-4 before:mr-2 before:content-['•'] ${theme === 'dark' ? 'text-slate-300 before:text-lime-400' : 'text-slate-700 before:text-emerald-500 font-medium'}`}>{trimmed.slice(2)}</p>;
        }
        if (/^\d+\.\s/.test(trimmed)) {
          return <p key={index} className={`rounded-xl border p-2.5 font-mono text-[11px] leading-4 transition ${theme === 'dark' ? 'border-slate-800 bg-slate-900/50 text-slate-300' : 'border-slate-200 bg-slate-50 text-slate-700'}`}>{trimmed}</p>;
        }
        return <p key={index} className={`text-sm leading-relaxed ${theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}`}>{trimmed.replace(/`/g, '')}</p>;
      })}
    </div>
  );
}

function MessageContent({ message, theme = 'dark' }: { message: Message; theme?: 'light' | 'dark' }) {
  if (message.logResult) {
    return <LogAnalysisCard result={message.logResult} compact theme={theme} />;
  }
  return <RichText text={message.text} theme={theme} />;
}

function App() {
  const [activeSection, setActiveSection] = useState<Section>('chat');
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [draft, setDraft] = useState('');
  const [availableAgents, setAvailableAgents] = useState<Agent[]>(fallbackAgents);
  const [selectedAgent, setSelectedAgent] = useState('auto');
  const [attachments, setAttachments] = useState<File[]>([]);
  const [folderFiles, setFolderFiles] = useState<File[]>([]);
  const [folderPaths, setFolderPaths] = useState<string[]>([]);
  
  // ServiceNow operational States
  const [ticketId, setTicketId] = useState('INC00102');
  const [ticketResult, setTicketResult] = useState<string | null>(null);
  const [ticketDetails, setTicketDetails] = useState<any | null>(null);

  // Plugin / System States
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [pluginError, setPluginError] = useState<string | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [logResult, setLogResult] = useState<LogAnalysisResult | string | null>(null);
  const [isAnalyzingLogs, setIsAnalyzingLogs] = useState(false);

  // Relational Memory States
  const [sessions, setSessions] = useState<any[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Datetime range filtering states
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');

  // Live Log Tailing & Streaming states
  const [activeLogTab, setActiveLogTab] = useState<'scan' | 'stream'>('scan');
  const [isTailing, setIsTailing] = useState(false);
  const [tailFilePath, setTailFilePath] = useState('backend/logs/app.log');
  const [folderStreamPath, setFolderStreamPath] = useState('');
  const [availableStreamFiles, setAvailableStreamFiles] = useState<string[]>([]);
  const [isScanningStreamFolder, setIsScanningStreamFolder] = useState(false);
  const [tailLines, setTailLines] = useState<string[]>([]);
  const [tailResult, setTailResult] = useState<LogAnalysisResult | null>(null);
  const tailEventSourceRef = useRef<EventSource | null>(null);
  const terminalEndRef = useRef<HTMLDivElement | null>(null);
  
  const [streamRightTab, setStreamRightTab] = useState<'metrics' | 'deep'>('metrics');
  const [isAnalyzingStreamFile, setIsAnalyzingStreamFile] = useState(false);
  const [streamFileAnalysisResult, setStreamFileAnalysisResult] = useState<LogAnalysisResult | string | null>(null);
  const [tailError, setTailError] = useState<string | null>(null);
  
  // Real-time Event streaming states
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamRouting, setStreamRouting] = useState<string | null>(null);
  const [streamPlanning, setStreamPlanning] = useState<string | null>(null);
  const [streamExecution, setStreamExecution] = useState<string | null>(null);

  const currentAgent = useMemo(
    () => availableAgents.find((agent) => agent.id === selectedAgent),
    [selectedAgent, availableAgents]
  );

  const fetchSessions = async () => {
    try {
      const response = await fetch('/api/v1/sessions');
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (e) {
      console.error('Error fetching database sessions', e);
    }
  };

  const loadSession = async (sid: string) => {
    setCurrentSessionId(sid);
    try {
      const response = await fetch(`/api/v1/sessions/${sid}/messages`);
      if (response.ok) {
        const data = await response.json();
        setMessages([
          initialMessages[0],
          ...data.map((msg: any) => ({
            role: msg.role,
            text: msg.text,
            logResult: msg.metadata?.agent_id === 'log_analysis_agent' && msg.text.includes('{') ? JSON.parse(msg.text) : undefined
          }))
        ]);
      }
    } catch (e) {
      console.error('Error loading session details', e);
    }
  };

  const createNewSession = async () => {
    try {
      const response = await fetch('/api/v1/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Chat', agent_id: selectedAgent })
      });
      if (response.ok) {
        const newSession = await response.json();
        setCurrentSessionId(newSession.id);
        setMessages(initialMessages);
        fetchSessions();
      }
    } catch (e) {
      console.error('Error initializing new session', e);
    }
  };

  const deleteSession = async (sid: string) => {
    try {
      const response = await fetch(`/api/v1/sessions/${sid}`, { method: 'DELETE' });
      if (response.ok) {
        fetchSessions();
        if (currentSessionId === sid) {
          setCurrentSessionId(null);
          setMessages(initialMessages);
        }
      }
    } catch (e) {
      console.error('Error deleting session', e);
    }
  };

  const fetchAgents = async () => {
    try {
      const response = await fetch('/api/v1/agents');
      if (!response.ok) throw new Error(`Failed to load agents`);

      const data = await response.json();
      const loadedAgents = (data.agents ?? []) as Agent[];
      if (loadedAgents.length > 0) {
        const formattedList = [
          { id: 'auto', name: '⚡ Auto Router (SLM)' },
          ...loadedAgents.map(agent => ({
            ...agent,
            name: agent.id === 'log_analysis_agent'
              ? '📁 Log Analysis Agent'
              : agent.id === 'servicenow_agent'
              ? '🎫 ServiceNow Agent'
              : agent.id === 'github_actions_agent'
              ? '⚙️ GitHub Actions Agent'
              : agent.id === 'terraform_agent'
              ? '🛠️ Terraform Agent'
              : agent.id === 'ansible_agent'
              ? '⚡ Ansible Agent'
              : agent.id === 'monitoring_agent'
              ? '📊 Monitoring Agent'
              : agent.id === 'vmware_agent'
              ? '💾 VMware Agent'
              : agent.id === 'nutanix_agent'
              ? '🚀 Nutanix Agent'
              : agent.name
          }))
        ];
        setAvailableAgents(formattedList);
      }
    } catch (error) {
      setAgentError('Agent service unavailable. Operating in fallback mode.');
    }
  };

  const toggleAgent = async (agentId: string, currentEnabled: boolean) => {
    try {
      const endpoint = currentEnabled ? 'disable' : 'enable';
      const response = await fetch(`/api/v1/agents/${agentId}/${endpoint}`, { method: 'POST' });
      if (!response.ok) throw new Error(`Failed to toggle agent`);
      await fetchAgents();
    } catch (error) {
      console.error('Error toggling agent:', error);
    }
  };

  useEffect(() => {
    const fetchPlugins = async () => {
      try {
        const response = await fetch('/api/v1/plugins');
        if (!response.ok) throw new Error(`Failed to load plugins`);

        const data = await response.json();
        setPlugins(data.plugins ?? []);
      } catch (error) {
        setPluginError('Plugins metadata unavailable.');
      }
    };

    fetchAgents();
    fetchPlugins();
    fetchSessions();
  }, []);

  const sendMessage = async () => {
    if (!draft.trim()) return;

    const promptText = draft.trim();
    const userMsg: Message = { role: 'user', text: promptText };
    setMessages((prev) => [...prev, userMsg]);
    setDraft('');
    
    setIsStreaming(true);
    setStreamRouting('Awaiting orchestrator handshake...');
    setStreamPlanning(null);
    setStreamExecution(null);

    // Bootstrap persistent session ID if null
    let activeSessionId = currentSessionId;
    if (!activeSessionId) {
      activeSessionId = crypto.randomUUID();
      setCurrentSessionId(activeSessionId);
      fetchSessions();
    }

    // Append placeholder for assistant typing
    setMessages((prev) => [...prev, { role: 'assistant', text: '' }]);

    try {
      // 1. File Upload specialized trigger for logs and code/config validation
      let uploadAgent = selectedAgent;
      if (uploadAgent === 'auto' && attachments.length > 0) {
        const fileNames = attachments.map(f => f.name.toLowerCase());
        const hasTf = fileNames.some(name => name.endsWith('.tf') || name.endsWith('.hcl') || name.includes('tfplan'));
        const hasGithub = fileNames.some(name => name.includes('workflow') || name.includes('action') || name.includes('github') || name.includes('.github'));
        const hasAnsible = fileNames.some(name => name.includes('playbook') || name.includes('ansible') || name.endsWith('.yml') || name.endsWith('.yaml'));
        
        if (hasTf) {
          uploadAgent = 'terraform_agent';
        } else if (hasGithub) {
          uploadAgent = 'github_actions_agent';
        } else if (hasAnsible) {
          uploadAgent = 'ansible_agent';
        } else {
          uploadAgent = 'log_analysis_agent';
        }
      }

      if (fileEnabledAgents.has(uploadAgent) && attachments.length > 0) {
        const formData = new FormData();
        formData.append('intent', promptText);
        formData.append('session_id', activeSessionId);
        if (startTime) formData.append('start_time', startTime);
        if (endTime) formData.append('end_time', endTime);
        attachments.forEach((file) => {
          formData.append('files', file, file.name);
        });

        const response = await fetch(`/api/v1/agents/${uploadAgent}/analyze-files`, {
          method: 'POST',
          body: formData
        });

        if (!response.ok) throw new Error('Upload analysis failed');
        const data = await response.json();
        const result = data.result ?? {};
        
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'assistant',
            text: result.summary ?? 'Files processed.',
            logResult: uploadAgent === 'log_analysis_agent' ? result : undefined
          };
          return updated;
        });
        setAttachments([]);
        setStreamRouting(null);
        setIsStreaming(false);
        return;
      }

      // 2. Conversational Server-Sent Events (SSE) Stream Reader
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: activeSessionId,
          message: promptText,
          agent_id: selectedAgent,
          start_time: startTime || undefined,
          end_time: endTime || undefined
        })
      });

      if (!response.ok) throw new Error('Streaming connection failed');
      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');
      if (!reader) throw new Error('Readable stream not supported');

      let assistantText = '';
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the last segment in the buffer

        for (const line of lines) {
          const cleanLine = line.trim();
          if (!cleanLine || !cleanLine.startsWith('data: ')) continue;
          
          const jsonStr = cleanLine.slice(6);
          if (jsonStr === '[DONE]') continue;

          try {
            const payload = JSON.parse(jsonStr);
            if (payload.event === 'routing') {
              setStreamRouting(payload.data);
            } else if (payload.event === 'planning') {
              setStreamPlanning(payload.data);
            } else if (payload.event === 'execution') {
              setStreamExecution(payload.data);
            } else if (payload.event === 'token') {
              assistantText += payload.data;
              setMessages((prev) => {
                const updated = [...prev];
                if (updated.length > 0) {
                  updated[updated.length - 1] = {
                    role: 'assistant',
                    text: assistantText
                  };
                }
                return updated;
              });
            } else if (payload.event === 'session') {
              setCurrentSessionId(payload.session_id);
              fetchSessions(); // Auto-refresh relational sessions history
            } else if (payload.event === 'error') {
              assistantText += `\n\n⚠️ Error during processing: ${payload.data}`;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: 'assistant', text: assistantText };
                return updated;
              });
            }
          } catch (err) {
            console.error('Parser error in token line', err);
          }
        }
      }
    } catch (e) {
      const errDetail = e instanceof Error ? e.message : 'Timeout error';
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'assistant',
          text: `Orchestrator failed to streams details. Fallback mechanism loaded.\n\nDetail: ${errDetail}`
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;
    setAttachments(Array.from(files));
  };

  const handleFolder = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;
    const selectedFiles = Array.from(files);
    const paths = selectedFiles.map((file) => file.webkitRelativePath || file.name);
    setFolderFiles(selectedFiles);
    setFolderPaths(paths.slice(0, 12));
    setLogResult(null);
  };

  const analyzeSelectedLogs = async () => {
    if (folderFiles.length === 0) {
      setLogResult('Choose a folder with log files first.');
      return;
    }

    setIsAnalyzingLogs(true);
    setLogResult(null);

    const formData = new FormData();
    formData.append('intent', 'analyze logs from chosen folder');
    if (startTime) formData.append('start_time', startTime);
    if (endTime) formData.append('end_time', endTime);
    folderFiles.forEach((file) => {
      formData.append('files', file, file.webkitRelativePath || file.name);
    });

    try {
      const response = await fetch('/api/v1/agents/log_analysis_agent/analyze-files', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Logs aggregation failed');
      const data = await response.json();
      setLogResult(data.result ?? {});
    } catch (error) {
      setLogResult(error instanceof Error ? error.message : 'Parsing error');
    } finally {
      setIsAnalyzingLogs(false);
    }
  };

  const scanStreamFolder = async () => {
    if (!folderStreamPath.trim()) return;
    setIsScanningStreamFolder(true);
    setTailError(null);
    try {
      const response = await fetch(`/api/v1/logs/list-files?folder_path=${encodeURIComponent(folderStreamPath)}`);
      if (!response.ok) throw new Error('Failed to load logs list');
      const data = await response.json();
      setAvailableStreamFiles(data.files ?? []);
      if (data.files && data.files.length > 0) {
        setTailFilePath(data.files[0]);
      } else {
        setTailError("No `.log`, `.txt` or `.json` files found in the specified directory.");
      }
    } catch (e) {
      setTailError("Failed to list files. Check directory path and read permissions.");
    } finally {
      setIsScanningStreamFolder(false);
    }
  };

  const authorizeAndStartTailing = async () => {
    if (!tailFilePath.trim()) return;
    try {
      const formData = new FormData();
      formData.append('path', tailFilePath);
      await fetch('/api/v1/security/allow-path', {
        method: 'POST',
        body: formData
      });
    } catch (e) {
      console.warn("Path pre-authorization skipped", e);
    }
    startTailing();
  };

  const startTailing = () => {
    if (!tailFilePath.trim()) return;
    
    stopTailing();

    setIsTailing(true);
    setTailLines([]);
    setTailResult(null);
    setTailError(null);

    const queryParams = new URLSearchParams();
    queryParams.append('file_path', tailFilePath);
    if (startTime) queryParams.append('start_time', startTime);
    if (endTime) queryParams.append('end_time', endTime);

    const url = `/api/v1/agents/log_analysis_agent/tail?${queryParams.toString()}`;
    const ev = new EventSource(url);
    tailEventSourceRef.current = ev;

    ev.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'init') {
          setTailLines(data.raw_lines ?? []);
          setTailResult({
            files_analyzed: 1,
            total_entries: data.total_lines,
            classified_entries: {
              errors: Array(data.classified.error_count).fill({}),
              warnings: Array(data.classified.warning_count).fill({}),
              info: Array(data.classified.info_count).fill({})
            },
            patterns: data.patterns,
            application_status: data.application_status
          });
        } else if (data.event === 'update') {
          setTailLines((prev) => {
            const updated = [...prev, ...(data.raw_lines ?? [])];
            return updated.slice(-150);
          });
          setTailResult((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              total_entries: data.total_lines,
              classified_entries: {
                errors: Array(data.classified.error_count).fill({}),
                warnings: Array(data.classified.warning_count).fill({}),
                info: Array(data.classified.info_count).fill({})
              },
              patterns: data.patterns,
              application_status: data.application_status
            };
          });
        } else if (data.event === 'error') {
          console.error("Tail stream error: ", data.message);
          setTailError(data.message);
          stopTailing();
        }
      } catch (err) {
        console.error("Failed to parse tail event: ", err);
      }
    };

    ev.onerror = (err) => {
      console.error("SSE connection error: ", err);
      setTailError("SRE Permission Denied or SSE Connection Timeout. Please check target file permissions (e.g. read access) and active backend uvicorn state.");
      stopTailing();
    };
  };

  const stopTailing = () => {
    if (tailEventSourceRef.current) {
      tailEventSourceRef.current.close();
      tailEventSourceRef.current = null;
    }
    setIsTailing(false);
  };

  useEffect(() => {
    if (activeSection !== 'logs') {
      stopTailing();
    }
  }, [activeSection]);

  useEffect(() => {
    if (isTailing && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [tailLines, isTailing]);

  useEffect(() => {
    if (activeLogTab === 'scan') {
      stopTailing();
    }
  }, [activeLogTab]);

  const analyzeStreamFile = async () => {
    if (!tailFilePath.trim()) return;
    
    setIsAnalyzingStreamFile(true);
    setStreamRightTab('deep');
    setStreamFileAnalysisResult(null);

    const formData = new FormData();
    formData.append('intent', `analyze local log file at ${tailFilePath}`);
    formData.append('file_path', tailFilePath);
    if (startTime) formData.append('start_time', startTime);
    if (endTime) formData.append('end_time', endTime);
    if (currentSessionId) formData.append('session_id', currentSessionId);

    try {
      const response = await fetch('/api/v1/agents/log_analysis_agent/analyze-files', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Logs aggregation failed');
      }
      const data = await response.json();
      setStreamFileAnalysisResult(data.result ?? {});
    } catch (error) {
      setStreamFileAnalysisResult(error instanceof Error ? error.message : 'Parsing error');
    } finally {
      setIsAnalyzingStreamFile(false);
    }
  };

  // ServiceNow REST mock query
  const executeSNOWLookup = async () => {
    if (!ticketId.trim()) return;
    setTicketResult('Connecting to ServiceNow instance...');
    setTicketDetails(null);

    try {
      const response = await fetch('/api/v1/agents/servicenow_agent/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: 'servicenow_agent',
          input_data: {
            intent: `get details for ticket ${ticketId}`
          }
        })
      });

      if (response.ok) {
        const data = await response.json();
        const outcome = data.result ?? {};
        if (outcome.found) {
          setTicketDetails(outcome.incident);
          setTicketResult(null);
        } else {
          setTicketResult(`Ticket ID ${ticketId} not found in the database.`);
        }
      } else {
        setTicketResult('ServiceNow gateway timeout.');
      }
    } catch (e) {
      setTicketResult('Error executing ServiceNow search.');
    }
  };

  const renderLogResult = () => {
    if (!logResult) return null;
    if (typeof logResult === 'string') {
      return (
        <div className={`mt-4 rounded-xl border p-4 text-xs font-mono transition-all duration-300 ${theme === 'dark' ? 'border-amber-500/10 bg-amber-500/5 text-amber-400' : 'border-amber-500/20 bg-amber-50/50 text-amber-700'}`}>
          ⚠️ {logResult}
        </div>
      );
    }
    return <LogAnalysisCard result={logResult} theme={theme} />;
  };

  return (
    <div className={`min-h-screen font-sans antialiased selection:bg-lime-400 transition-colors duration-300 ${theme === 'dark' ? 'bg-slate-950 text-slate-100 selection:text-slate-950' : 'bg-slate-50 text-slate-900 selection:text-white'}`}>
      <div className="mx-auto flex min-h-screen max-w-full flex-col px-4 py-4 sm:px-6 lg:px-8">
        
        {/* ========================================== HEADER ========================================== */}
        <header className={`mb-4 flex items-center justify-between rounded-3xl border px-6 py-4 shadow-xl backdrop-blur-xl transition-all duration-300 ${theme === 'dark' ? 'border-slate-800/80 bg-slate-900/40' : 'border-slate-200/85 bg-white/75'}`}>
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <p className={`text-[10px] font-bold uppercase tracking-[0.25em] ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>On-Premises SLM Infrastructure</p>
            </div>
            <h1 className="mt-1 text-2xl font-black bg-gradient-to-r from-lime-400 to-emerald-400 bg-clip-text text-transparent">SLM AI Operations Platform</h1>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              className={`rounded-full border px-4.5 py-2 text-xs font-semibold flex items-center gap-1.5 transition-all duration-200 ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-200 hover:bg-slate-800' : 'border-slate-300 bg-slate-50 text-slate-700 hover:bg-slate-100'}`}
              onClick={() => setTheme((v) => (v === 'dark' ? 'light' : 'dark'))}
            >
              {theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode'}
            </button>
            <div className="rounded-full bg-lime-400/15 border border-lime-400/20 px-3.5 py-1 text-xs font-bold text-lime-400">Enterprise Operator</div>
          </div>
        </header>

        <div className="grid flex-1 gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
          
          {/* ========================================== SIDEBAR ========================================== */}
          <aside className={`flex flex-col rounded-3xl border p-4 shadow-xl backdrop-blur-xl transition-all duration-300 ${theme === 'dark' ? 'border-slate-800/60 bg-slate-900/20' : 'border-slate-200/70 bg-white/40'}`}>
            <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-3 px-1">Navigation Systems</p>
            <nav className="space-y-1">
              {sections.map((sec) => (
                <button
                  key={sec.id}
                  type="button"
                  onClick={() => setActiveSection(sec.id)}
                  className={`w-full rounded-2xl px-4 py-2.5 text-left text-xs font-semibold transition-all duration-200 ${activeSection === sec.id ? 'bg-lime-400 text-slate-950 shadow-soft' : theme === 'dark' ? 'text-slate-300 hover:bg-slate-900/60' : 'text-slate-700 hover:bg-slate-200/50'}`}
                >
                  {sec.label}
                </button>
              ))}
            </nav>

            {/* PERSISTENT MEMORY SIDEBAR SECTION */}
            <div className="mt-6 flex-1 flex flex-col min-h-[220px]">
              <div className="flex items-center justify-between mb-2.5 px-1">
                <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">Conversations Memory</p>
                <button
                  onClick={createNewSession}
                  className="text-[10px] font-bold text-lime-400 hover:text-lime-300 transition"
                  title="Start New Thread"
                >
                  + New Chat
                </button>
              </div>

              <div className="flex-1 overflow-y-auto max-h-[300px] space-y-1.5 pr-1">
                {sessions.length === 0 ? (
                  <p className="text-[11px] text-slate-500 italic px-2">No past active sessions found.</p>
                ) : (
                  sessions.map((sess) => (
                    <div
                      key={sess.id}
                      className={`group flex items-center justify-between rounded-xl px-3 py-2 text-xs border transition cursor-pointer ${currentSessionId === sess.id ? (theme === 'dark' ? 'bg-slate-900/80 border-slate-700/80 text-lime-400' : 'bg-lime-50 border-lime-200 text-lime-600') : (theme === 'dark' ? 'bg-slate-950/20 border-transparent text-slate-400 hover:bg-slate-900/30' : 'bg-slate-100/50 border-transparent text-slate-500 hover:bg-slate-200/40')}`}
                    >
                      <span className="truncate flex-1 pr-2 font-medium" onClick={() => loadSession(sess.id)}>
                        💬 {sess.title}
                      </span>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteSession(sess.id); }}
                        className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition text-[10px] pl-1.5"
                        title="Delete Session"
                      >
                        ✕
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className={`mt-4 rounded-2xl border p-3 text-[11px] transition-all duration-300 ${theme === 'dark' ? 'border-slate-800 bg-slate-950/40 text-slate-500' : 'border-slate-200 bg-slate-100/50 text-slate-650'}`}>
              <p className={`font-bold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}`}>Local Architecture Validated</p>
              <p className="mt-1 leading-5">Running offline. Routing requests via internal Python adapters to Qwen 1.5B.</p>
            </div>
          </aside>

          {/* ========================================== MAIN WORKSPACE ========================================== */}
          <main className="space-y-4">
            
            {/* 1. CHAT STREAMING SECTION */}
            {activeSection === 'chat' && (
              <section className={`rounded-3xl border p-5 shadow-2xl backdrop-blur-xl transition-all duration-300 ${theme === 'dark' ? 'border-slate-800/80 bg-slate-900/35' : 'border-slate-200 bg-white'}`}>
                <div className={`mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b pb-4 ${theme === 'dark' ? 'border-slate-800/60' : 'border-slate-100'}`}>
                  <div>
                    <h2 className={`text-xl font-black ${theme === 'dark' ? 'text-slate-50' : 'text-slate-900'}`}>Interactive AI Operations Panel</h2>
                    <p className={`mt-1 text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Stream natural-language commands and observe SLM task classification.</p>
                  </div>

                  <div className="flex items-center gap-3">
                    <label className={`flex items-center gap-2 rounded-2xl border px-4.5 py-2 text-xs transition ${theme === 'dark' ? 'border-slate-800 bg-slate-950' : 'border-slate-250 bg-slate-50'}`}>
                      <span className={`${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>Target Agent:</span>
                      <select
                        value={selectedAgent}
                        onChange={(e) => setSelectedAgent(e.target.value)}
                        className={`bg-transparent text-xs font-bold outline-none cursor-pointer ${theme === 'dark' ? 'text-lime-400' : 'text-emerald-600'}`}
                      >
                        {availableAgents.map((ag) => (
                          <option key={ag.id} value={ag.id} className={theme === 'dark' ? 'bg-slate-950 text-slate-100' : 'bg-white text-slate-900'}>{ag.name}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                </div>

                {/* LOGS STREAMING ACTIONS INDICATORS OVERLAY */}
                {isStreaming && (
                  <div className={`mb-3 rounded-2xl border p-3.5 text-xs animate-pulse space-y-1 ${theme === 'dark' ? 'border-lime-400/20 bg-lime-400/5 text-slate-300' : 'border-emerald-500/20 bg-emerald-50/40 text-slate-700'}`}>
                    <p className={`font-bold ${theme === 'dark' ? 'text-lime-400' : 'text-emerald-600'}`}>⚡ Live Agent Stream Execution Pipeline</p>
                    {streamRouting && <p className={`pl-3 ${theme === 'dark' ? 'text-slate-250' : 'text-slate-800'}`}>🔍 **Routing**: {streamRouting}</p>}
                    {streamPlanning && <p className={`pl-3 ${theme === 'dark' ? 'text-slate-250' : 'text-slate-800'}`}>📋 **Planning**: {streamPlanning}</p>}
                    {streamExecution && <p className={`pl-3 ${theme === 'dark' ? 'text-slate-250' : 'text-slate-800'}`}>⚙️ **Execution**: {streamExecution}</p>}
                  </div>
                )}

                {/* 🕒 DATETIME RANGE FILTER BOUNDARY */}
                {selectedAgent === 'log_analysis_agent' && (
                  <div className={`mb-4 rounded-2xl border p-3 flex flex-col md:flex-row gap-3 items-center justify-between transition-all duration-300 ${theme === 'dark' ? 'border-slate-800 bg-slate-950/40 text-slate-300' : 'border-slate-200 bg-slate-50/50 text-slate-700'}`}>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-lg">🕒</span>
                      <div className="text-left">
                        <p className={`font-bold ${theme === 'dark' ? 'text-slate-200' : 'text-slate-850'}`}>Datetime Boundary Filter</p>
                        <p className={`text-[10px] ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>Limit log parser analysis or search to a specific range.</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2.5">
                      <div className="flex items-center gap-1.5 text-[10px]">
                        <span className={theme === 'dark' ? 'text-slate-450' : 'text-slate-500'}>Start:</span>
                        <input
                          type="datetime-local"
                          value={startTime}
                          onChange={(e) => setStartTime(e.target.value)}
                          className={`rounded-lg border px-2.5 py-1 transition text-[10px] w-44 outline-none ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-100 focus:border-lime-400' : 'border-slate-250 bg-white text-slate-800 focus:border-emerald-550'}`}
                        />
                      </div>
                      <div className="flex items-center gap-1.5 text-[10px]">
                        <span className={theme === 'dark' ? 'text-slate-450' : 'text-slate-500'}>End:</span>
                        <input
                          type="datetime-local"
                          value={endTime}
                          onChange={(e) => setEndTime(e.target.value)}
                          className={`rounded-lg border px-2.5 py-1 transition text-[10px] w-44 outline-none ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-100 focus:border-lime-400' : 'border-slate-250 bg-white text-slate-800 focus:border-emerald-550'}`}
                        />
                      </div>
                      {(startTime || endTime) && (
                        <button
                          onClick={() => { setStartTime(''); setEndTime(''); }}
                          className={`rounded px-2.5 py-1 text-[10px] font-bold border transition ${theme === 'dark' ? 'border-red-500/20 bg-red-500/10 text-red-400 hover:bg-red-500/20' : 'border-red-200 bg-red-50 text-red-650 hover:bg-red-105'}`}
                        >
                          Clear
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* MESSAGES VIEW WINDOW */}
                <div className={`mb-4 max-h-[360px] overflow-y-auto space-y-3.5 rounded-3xl border p-4 ${theme === 'dark' ? 'border-slate-800 bg-slate-950/70' : 'border-slate-250 bg-slate-50/50'}`}>
                  {messages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`rounded-2xl p-4.5 border text-xs max-w-[85%] transition-all duration-200 ${
                        msg.role === 'assistant'
                          ? theme === 'dark'
                            ? 'border-slate-800/80 bg-slate-900/40 text-slate-200 mr-auto'
                            : 'border-slate-200 bg-white text-slate-800 mr-auto shadow-sm'
                          : msg.role === 'user'
                            ? theme === 'dark'
                              ? 'border-slate-700/60 bg-slate-800/60 text-slate-100 ml-auto'
                              : 'border-lime-200 bg-lime-50/50 text-slate-850 ml-auto shadow-sm'
                            : theme === 'dark'
                              ? 'border-slate-900 bg-slate-950 text-slate-500 italic max-w-full text-center'
                              : 'border-slate-200 bg-slate-100/50 text-slate-400 italic max-w-full text-center'
                      }`}
                    >
                      <div className={`mb-1.5 text-[9px] font-bold uppercase tracking-wider ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>
                        {msg.role === 'assistant' ? '🤖 SLM Operations Assistant' : msg.role === 'user' ? '👤 operator' : '⚙️ system'}
                      </div>
                      <MessageContent message={msg} theme={theme} />
                    </div>
                  ))}
                </div>

                {/* INPUT ZONE */}
                <div className={`rounded-3xl border p-3 transition-all duration-300 ${theme === 'dark' ? 'border-slate-800 bg-slate-950/80' : 'border-slate-250 bg-white shadow-sm'}`}>
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                    placeholder="Ask standard SRE questions or route tickets (e.g. 'find database connection errors' or 'lookup ticket INC00101')..."
                    className={`min-h-[90px] w-full resize-none rounded-2xl border border-transparent bg-transparent px-3 py-2 text-xs outline-none transition ${theme === 'dark' ? 'text-slate-100 placeholder:text-slate-500 focus:placeholder:text-slate-600' : 'text-slate-800 placeholder:text-slate-400 focus:placeholder:text-slate-500'}`}
                  />
                  <div className={`flex items-center justify-between border-t pt-2.5 px-1.5 ${theme === 'dark' ? 'border-slate-900' : 'border-slate-100'}`}>
                    {fileEnabledAgents.has(selectedAgent) ? (
                      <label className={`flex items-center gap-2 text-xs cursor-pointer transition ${theme === 'dark' ? 'text-slate-500 hover:text-slate-300' : 'text-slate-400 hover:text-slate-600'}`}>
                        <input type="file" multiple onChange={handleFiles} className="hidden" />
                        <span className={`rounded-full border px-3 py-1.5 transition ${theme === 'dark' ? 'border-slate-800 bg-slate-900 hover:bg-slate-800' : 'border-slate-200 bg-slate-50 hover:bg-slate-100'}`}>
                          {selectedAgent === 'log_analysis_agent' ? '📁 Add log file attachment' : '📎 Add code/config files'}
                        </span>
                        {attachments.length > 0 && <span className={`text-[10px] font-bold ${theme === 'dark' ? 'text-lime-400' : 'text-emerald-600'}`}>({attachments.length} selected)</span>}
                      </label>
                    ) : <div />}
                    
                    <button
                      type="button"
                      onClick={sendMessage}
                      disabled={!draft.trim() && attachments.length === 0}
                      className={`rounded-full px-6 py-2 text-xs font-bold shadow-soft transition disabled:opacity-30 disabled:cursor-not-allowed ${theme === 'dark' ? 'bg-lime-400 text-slate-950 hover:bg-lime-300' : 'bg-emerald-500 text-white hover:bg-emerald-600'}`}
                    >
                      Stream Prompt
                    </button>
                  </div>
                </div>
              </section>
            )}

            {/* 2. DIRECTORIES LOG SCANNER & STREAMER */}
            {activeSection === 'logs' && (
              <section className={`rounded-3xl border p-5 shadow-2xl backdrop-blur-xl transition-all duration-300 ${theme === 'dark' ? 'border-slate-800/80 bg-slate-900/35' : 'border-slate-200 bg-white'}`}>
                {/* 🎛️ SUB-TAB SWITCHER */}
                <div className="mb-6 flex gap-2 border-b pb-3 border-slate-800/20">
                  <button
                    onClick={() => setActiveLogTab('scan')}
                    className={`rounded-2xl px-4.5 py-2 text-xs font-bold transition flex items-center gap-1.5 ${activeLogTab === 'scan' ? 'bg-lime-400 text-slate-950 shadow-soft' : theme === 'dark' ? 'text-slate-300 hover:bg-slate-800/60' : 'text-slate-700 hover:bg-slate-200/50'}`}
                  >
                    📁 Folder Scanner
                  </button>
                  <button
                    onClick={() => setActiveLogTab('stream')}
                    className={`rounded-2xl px-4.5 py-2 text-xs font-bold transition flex items-center gap-1.5 ${activeLogTab === 'stream' ? 'bg-lime-400 text-slate-950 shadow-soft' : theme === 'dark' ? 'text-slate-300 hover:bg-slate-800/60' : 'text-slate-700 hover:bg-slate-200/50'}`}
                  >
                    ⚡ Real-time Streamer
                  </button>
                </div>

                {activeLogTab === 'scan' ? (
                  <>
                    <div className={`flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b pb-4 ${theme === 'dark' ? 'border-slate-800/60' : 'border-slate-100'}`}>
                      <div>
                        <h2 className={`text-xl font-black ${theme === 'dark' ? 'text-slate-50' : 'text-slate-900'}`}>Local Log Folders Scanner</h2>
                        <p className={`mt-1 text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Map an entire directory of logs recursively to analyze error signatures.</p>
                      </div>
                      <label className={`rounded-full border px-4.5 py-2.5 text-xs font-bold cursor-pointer transition ${theme === 'dark' ? 'border-slate-700 bg-slate-950 text-slate-300 hover:bg-slate-900' : 'border-slate-250 bg-slate-50 text-slate-700 hover:bg-slate-100'}`}>
                        📁 Pick Directory
                        {/* @ts-ignore */}
                        <input type="file" webkitdirectory="true" directory={true as any} multiple className="hidden" onChange={handleFolder} />
                      </label>
                    </div>

                    {/* 🕒 DATETIME RANGE FILTER BOUNDARY */}
                    <div className={`mt-4 rounded-2xl border p-3 flex flex-col md:flex-row gap-3 items-center justify-between transition-all duration-300 ${theme === 'dark' ? 'border-slate-800 bg-slate-950/40 text-slate-300' : 'border-slate-200 bg-slate-50/50 text-slate-700'}`}>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-lg">🕒</span>
                        <div className="text-left">
                          <p className={`font-bold ${theme === 'dark' ? 'text-slate-200' : 'text-slate-850'}`}>Datetime Boundary Filter</p>
                          <p className={`text-[10px] ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>Limit log parser analysis to a specific range.</p>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2.5">
                        <div className="flex items-center gap-1.5 text-[10px]">
                          <span className={theme === 'dark' ? 'text-slate-450' : 'text-slate-500'}>Start:</span>
                          <input
                            type="datetime-local"
                            value={startTime}
                            onChange={(e) => setStartTime(e.target.value)}
                            className={`rounded-lg border px-2.5 py-1 transition text-[10px] w-44 outline-none ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-100 focus:border-lime-400' : 'border-slate-250 bg-white text-slate-800 focus:border-emerald-550'}`}
                          />
                        </div>
                        <div className="flex items-center gap-1.5 text-[10px]">
                          <span className={theme === 'dark' ? 'text-slate-450' : 'text-slate-500'}>End:</span>
                          <input
                            type="datetime-local"
                            value={endTime}
                            onChange={(e) => setEndTime(e.target.value)}
                            className={`rounded-lg border px-2.5 py-1 transition text-[10px] w-44 outline-none ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-100 focus:border-lime-400' : 'border-slate-250 bg-white text-slate-800 focus:border-emerald-550'}`}
                          />
                        </div>
                        {(startTime || endTime) && (
                          <button
                            onClick={() => { setStartTime(''); setEndTime(''); }}
                            className={`rounded px-2.5 py-1 text-[10px] font-bold border transition ${theme === 'dark' ? 'border-red-500/20 bg-red-500/10 text-red-400 hover:bg-red-500/20' : 'border-red-200 bg-red-50 text-red-650 hover:bg-red-105'}`}
                          >
                            Clear
                          </button>
                        )}
                      </div>
                    </div>

                    <div className={`mt-4 rounded-2xl border p-4 transition ${theme === 'dark' ? 'border-slate-800/80 bg-slate-950/40' : 'border-slate-200 bg-slate-50/50'}`}>
                      {folderPaths.length === 0 ? (
                        <p className={`text-xs italic ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>No operational directories loaded yet.</p>
                      ) : (
                        <div className="space-y-3 text-xs">
                          <p className={`font-bold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}`}>Identified Files Matrix ({folderFiles.length} files)</p>
                          <ul className="grid grid-cols-2 gap-2 font-mono text-[10px]">
                            {folderPaths.map((path) => (
                              <li key={path} className={`truncate p-1.5 rounded border transition ${theme === 'dark' ? 'bg-slate-900/60 border-slate-800/40 text-slate-400' : 'bg-white border-slate-200 text-slate-650'}`}>✓ {path}</li>
                            ))}
                          </ul>
                          
                          <button
                            type="button"
                            onClick={analyzeSelectedLogs}
                            disabled={isAnalyzingLogs}
                            className={`mt-2 rounded-full px-5 py-2.5 text-xs font-bold transition disabled:opacity-40 ${theme === 'dark' ? 'bg-lime-400 text-slate-950 hover:bg-lime-300' : 'bg-emerald-500 text-white hover:bg-emerald-600'}`}
                          >
                            {isAnalyzingLogs ? 'Indexing & Parsing...' : 'Run Diagnostics Engine'}
                          </button>
                        </div>
                      )}
                    </div>
                    {renderLogResult()}
                  </>
                ) : (
                  <div className="space-y-6">
                    {/* Stream Configuration Header */}
                    <div className={`flex flex-col gap-4 p-5 rounded-3xl border transition ${theme === 'dark' ? 'border-slate-800 bg-slate-900/40' : 'border-slate-200 bg-white'}`}>
                      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                        <div>
                          <h3 className={`text-md font-bold ${theme === 'dark' ? 'text-slate-100' : 'text-slate-900'}`}>⚡ Live Log Streamer</h3>
                          <p className={`text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>Tail any server log file dynamically via SSE and view real-time diagnostics.</p>
                        </div>
                        <div className="flex items-center gap-2.5 flex-wrap">
                          <button
                            type="button"
                            onClick={analyzeStreamFile}
                            disabled={isAnalyzingStreamFile}
                            className={`rounded-full px-5 py-2.5 text-xs font-bold transition shadow-md flex items-center gap-2 ${
                              theme === 'dark' ? 'bg-amber-400 text-slate-950 hover:bg-amber-300' : 'bg-amber-500 text-white hover:bg-amber-600'
                            }`}
                          >
                            {isAnalyzingStreamFile ? (
                              <>
                                <span className="animate-spin rounded-full h-3 w-3 border-2 border-slate-950 border-t-transparent"></span>
                                Analyzing...
                              </>
                            ) : (
                              <>🧠 Run Deep Analysis</>
                            )}
                          </button>
                          
                          <button
                            type="button"
                            onClick={isTailing ? stopTailing : authorizeAndStartTailing}
                            className={`rounded-full px-6 py-2.5 text-xs font-bold transition shadow-md flex items-center gap-2 ${
                              isTailing 
                                ? 'bg-red-500 text-white hover:bg-red-650 animate-pulse' 
                                : theme === 'dark' ? 'bg-lime-400 text-slate-950 hover:bg-lime-300' : 'bg-emerald-500 text-white hover:bg-emerald-600'
                            }`}
                          >
                            {isTailing ? (
                              <>
                                <span className="relative flex h-2 w-2">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
                                  <span className="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
                                </span>
                                Stop Tailing
                              </>
                            ) : (
                              <>▶ Start Tailing</>
                            )}
                          </button>
                        </div>
                      </div>

                      <div className="grid gap-4 md:grid-cols-3">
                        <div className="flex flex-col gap-1 md:col-span-2">
                          <span className={`text-[10px] font-bold uppercase tracking-wider ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Scan System Log Directory</span>
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={folderStreamPath}
                              onChange={(e) => setFolderStreamPath(e.target.value)}
                              disabled={isTailing}
                              placeholder="e.g. /home/arun/Workspace/backend/logs or C:\Logs"
                              className={`flex-1 rounded-xl border px-3.5 py-2 text-xs font-mono outline-none transition ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-100 focus:border-lime-400' : 'border-slate-250 bg-white text-slate-800 focus:border-emerald-550'}`}
                            />
                            <button
                              type="button"
                              onClick={scanStreamFolder}
                              disabled={isTailing || isScanningStreamFolder}
                              className={`rounded-xl px-4 py-2 text-xs font-bold transition ${theme === 'dark' ? 'bg-slate-800 text-lime-400 hover:bg-slate-700' : 'bg-slate-100 text-slate-750 hover:bg-slate-200'}`}
                            >
                              {isScanningStreamFolder ? 'Scanning...' : 'List Files'}
                            </button>
                          </div>
                        </div>

                        <div className="flex flex-col gap-1">
                          <span className={`text-[10px] font-bold uppercase tracking-wider ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Select Target Log File</span>
                          {availableStreamFiles.length > 0 ? (
                            <select
                              value={tailFilePath}
                              onChange={(e) => setTailFilePath(e.target.value)}
                              disabled={isTailing}
                              className={`rounded-xl border px-3 py-2 text-xs font-mono outline-none cursor-pointer transition ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-100 focus:border-lime-400' : 'border-slate-250 bg-white text-slate-800 focus:border-emerald-550'}`}
                            >
                              {availableStreamFiles.map((file) => (
                                <option key={file} value={file}>{file.split(/[\\/]/).pop() || file}</option>
                              ))}
                            </select>
                          ) : (
                            <input
                              type="text"
                              value={tailFilePath}
                              onChange={(e) => setTailFilePath(e.target.value)}
                              disabled={isTailing}
                              placeholder="e.g. backend/logs/app.log"
                              className={`rounded-xl border px-3.5 py-2 text-xs font-mono outline-none transition ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-100 focus:border-lime-400 disabled:opacity-50' : 'border-slate-250 bg-white text-slate-800 focus:border-emerald-550 disabled:opacity-50'}`}
                            />
                          )}
                        </div>
                      </div>

                      <div className="grid gap-4 md:grid-cols-3">
                        <div className="flex flex-col gap-1 md:col-span-2">
                          <span className={`text-[10px] font-bold uppercase tracking-wider ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Active Log Target Path</span>
                          <input
                            type="text"
                            value={tailFilePath}
                            onChange={(e) => setTailFilePath(e.target.value)}
                            disabled={isTailing}
                            className={`rounded-xl border px-3.5 py-2 text-xs font-mono outline-none transition ${theme === 'dark' ? 'border-slate-800 bg-slate-950 text-lime-400' : 'border-slate-250 bg-slate-50 text-emerald-650'}`}
                          />
                        </div>

                        <div className="flex flex-col gap-1">
                          <span className={`text-[10px] font-bold uppercase tracking-wider ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Optional Time Filter</span>
                          <div className="flex gap-2">
                            <input
                              type="datetime-local"
                              value={startTime}
                              onChange={(e) => setStartTime(e.target.value)}
                              disabled={isTailing}
                              className={`rounded-xl border px-2.5 py-1 text-[10px] w-full outline-none transition ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-100 focus:border-lime-400 disabled:opacity-50' : 'border-slate-250 bg-white text-slate-800 focus:border-emerald-550 disabled:opacity-50'}`}
                            />
                            <input
                              type="datetime-local"
                              value={endTime}
                              onChange={(e) => setEndTime(e.target.value)}
                              disabled={isTailing}
                              className={`rounded-xl border px-2.5 py-1 text-[10px] w-full outline-none transition ${theme === 'dark' ? 'border-slate-800 bg-slate-900 text-slate-100 focus:border-lime-400 disabled:opacity-50' : 'border-slate-250 bg-white text-slate-800 focus:border-emerald-550 disabled:opacity-50'}`}
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* ⚠️ Tailing Engine Warning / SRE Alert Banner */}
                    {tailError && (
                      <div className={`p-4.5 rounded-3xl border transition-all duration-300 ${
                        theme === 'dark' 
                          ? 'border-red-900/60 bg-red-950/30 text-red-200' 
                          : 'border-red-200 bg-red-50 text-red-800'
                      }`}>
                        <div className="flex items-start gap-3">
                          <span className="text-xl leading-none">⚠️</span>
                          <div className="flex-1 space-y-1.5">
                            <h4 className="text-xs font-bold uppercase tracking-wider">Tailing Engine Warning / SRE Alert</h4>
                            <p className="text-xs leading-relaxed">{tailError}</p>
                            <div className={`mt-2 p-2.5 rounded-xl font-mono text-[10px] ${
                              theme === 'dark' ? 'bg-slate-950/80 text-amber-400' : 'bg-slate-100 text-amber-800'
                            }`}>
                              <span className="font-bold">Suggested Remediation:</span>
                              <div className="mt-1 font-semibold select-all bg-slate-900/40 p-1.5 rounded border border-slate-800/40">
                                chmod +r {tailFilePath || 'your_log_file.log'}
                              </div>
                              <span className="text-[9px] text-slate-500 italic block mt-1">Verify file existence, verify read permission, and make sure the file is in an allowed workspace directory.</span>
                            </div>
                          </div>
                          <button 
                            onClick={() => setTailError(null)} 
                            className={`text-xs font-bold px-2.5 py-1 rounded-lg border transition ${
                              theme === 'dark' 
                                ? 'border-red-800/40 hover:bg-red-900/20 text-red-300' 
                                : 'border-red-200 hover:bg-red-100 text-red-700'
                            }`}
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Split View Console Grid */}
                    <div className="grid gap-4 lg:grid-cols-2">
                      {/* Left: Terminal Console */}
                      <div className="flex flex-col gap-2">
                        <div className="flex justify-between items-center px-1">
                          <span className={`text-[10px] font-bold uppercase tracking-wider ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Raw Tail Stream</span>
                          <span className={`text-[10px] font-mono ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>Showing last {tailLines.length} lines</span>
                        </div>
                        
                        <div className={`rounded-3xl border p-4 font-mono text-[11px] h-[400px] overflow-y-auto leading-relaxed shadow-inner flex flex-col justify-start relative transition-all duration-300 bg-slate-950 border-slate-850 text-slate-100`}>
                          {/* Console header */}
                          <div className="flex items-center gap-1.5 border-b border-slate-800/80 pb-2 mb-3">
                            <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
                            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
                            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                            <span className="ml-2 text-[9px] text-slate-500 font-bold uppercase tracking-wider">SRE Tail Console</span>
                          </div>

                          <div className="flex-1 space-y-1 overflow-y-auto pr-1">
                            {tailLines.length === 0 ? (
                              <div className="h-full flex flex-col items-center justify-center text-slate-500 italic text-xs py-10">
                                {isTailing ? (
                                  <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-lime-400 mb-2"></div>
                                    Listening for new log events...
                                  </>
                                ) : (
                                  'Terminal is offline. Click "Start Tailing" above to stream.'
                                )}
                              </div>
                            ) : (
                              tailLines.map((line, idx) => {
                                const getLineColorClass = (l: string) => {
                                  const upper = l.toUpperCase();
                                  if (upper.includes('ERROR') || upper.includes('FATAL') || upper.includes('EXCEPTION')) {
                                    return 'text-red-400 font-semibold bg-red-950/20 px-1 rounded';
                                  }
                                  if (upper.includes('WARN') || upper.includes('WARNING')) {
                                    return 'text-amber-400 bg-amber-950/20 px-1 rounded';
                                  }
                                  if (upper.includes('INFO')) {
                                    return 'text-sky-400';
                                  }
                                  if (upper.includes('DEBUG') || upper.includes('TRACE')) {
                                    return 'text-slate-500 font-light';
                                  }
                                  return 'text-slate-200';
                                };
                                return (
                                  <div key={idx} className={`${getLineColorClass(line)} truncate font-mono select-all`} title={line}>
                                    <span className="text-slate-650 select-none mr-2 font-light text-[9px]">{String(idx+1).padStart(3, '0')}</span>
                                    {line}
                                  </div>
                                );
                              })
                            )}
                            <div ref={terminalEndRef} />
                          </div>
                        </div>
                      </div>

                      {/* Right: Diagnostic analysis */}
                      <div className="flex flex-col gap-2">
                        <div className="flex justify-between items-center px-1">
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => setStreamRightTab('metrics')}
                              className={`rounded-lg px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition ${
                                streamRightTab === 'metrics'
                                  ? theme === 'dark' ? 'bg-slate-800 text-lime-400' : 'bg-slate-200 text-slate-800'
                                  : theme === 'dark' ? 'text-slate-400 hover:text-slate-200' : 'text-slate-500 hover:text-slate-850'
                              }`}
                            >
                              ⚡ Metrics
                            </button>
                            <button
                              type="button"
                              onClick={() => setStreamRightTab('deep')}
                              className={`rounded-lg px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition ${
                                streamRightTab === 'deep'
                                  ? theme === 'dark' ? 'bg-slate-800 text-lime-400' : 'bg-slate-200 text-slate-800'
                                  : theme === 'dark' ? 'text-slate-400 hover:text-slate-200' : 'text-slate-500 hover:text-slate-850'
                              }`}
                            >
                              🧠 Deep SRE Diagnostics
                            </button>
                          </div>
                          
                          {streamRightTab === 'metrics' && tailResult && (
                            <span className="rounded bg-lime-500/10 text-lime-400 text-[9px] px-1.5 py-0.5 border border-lime-500/20 font-mono">
                              Active Engine
                            </span>
                          )}
                        </div>

                        {streamRightTab === 'metrics' ? (
                          tailResult ? (
                            <div className="h-[400px] overflow-y-auto pr-1">
                              <LogAnalysisCard result={tailResult} theme={theme} />
                            </div>
                          ) : (
                            <div className={`rounded-3xl border h-[400px] flex flex-col items-center justify-center p-8 text-center transition bg-slate-950/40 border-slate-850/80`}>
                              <span className="text-3xl mb-3 animate-pulse">📊</span>
                              <h4 className={`text-sm font-bold text-slate-350`}>Diagnostics Standby</h4>
                              <p className="mt-2 text-xs text-slate-550 max-w-xs leading-relaxed">
                                {isTailing 
                                  ? 'Analyzing logs in real-time. Results will generate automatically as log patterns are detected.'
                                  : 'Start the tail streamer to view live aggregate statistics, application lifecycle boot details, and SRE error remediation cards.'}
                              </p>
                            </div>
                          )
                        ) : (
                          streamFileAnalysisResult ? (
                            typeof streamFileAnalysisResult === 'string' ? (
                              <div className={`rounded-3xl border p-4 text-xs font-mono h-[400px] overflow-y-auto transition border-red-500/20 bg-red-500/5 text-red-400`}>
                                ⚠️ {streamFileAnalysisResult}
                              </div>
                            ) : (
                              <div className="h-[400px] overflow-y-auto pr-1">
                                <LogAnalysisCard result={streamFileAnalysisResult} theme={theme} />
                              </div>
                            )
                          ) : (
                            <div className={`rounded-3xl border h-[400px] flex flex-col items-center justify-center p-8 text-center transition bg-slate-950/40 border-slate-850/80`}>
                              <span className="text-3xl mb-3">🧠</span>
                              <h4 className={`text-sm font-bold text-slate-350`}>Deep Diagnostics Ready</h4>
                              <p className="mt-2 text-xs text-slate-550 max-w-xs leading-relaxed">
                                Click the "🧠 Run Deep SRE Analysis" button to run complete comprehensive diagnostics on the full log file path with detailed aggregate metrics, pattern detections, and direct SRE remediation strategies.
                              </p>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* 3. SERVICENOW METRICS VISUALIZER */}
            {activeSection === 'snow' && (
              <section className={`rounded-3xl border p-5 shadow-2xl backdrop-blur-xl space-y-4 transition-all duration-300 ${theme === 'dark' ? 'border-slate-800/80 bg-slate-900/35' : 'border-slate-200 bg-white'}`}>
                <div>
                  <h2 className={`text-xl font-black ${theme === 'dark' ? 'text-slate-50' : 'text-slate-900'}`}>ServiceNow ITSM Gateway</h2>
                  <p className={`mt-1 text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Query mock incidents directly from local offline database tables.</p>
                </div>

                <div className="grid gap-3 sm:grid-cols-[1fr_120px]">
                  <input
                    type="text"
                    value={ticketId}
                    onChange={(e) => setTicketId(e.target.value)}
                    className={`rounded-full border px-5 py-2.5 text-xs outline-none transition ${theme === 'dark' ? 'border-slate-800 bg-slate-950/80 text-slate-100 focus:border-lime-400/80' : 'border-slate-250 bg-slate-50 text-slate-800 focus:border-emerald-550'}`}
                    placeholder="Enter incident ID (e.g. INC00101, INC00102)..."
                  />
                  <button
                    onClick={executeSNOWLookup}
                    className={`rounded-full px-6 py-2.5 text-xs font-bold transition ${theme === 'dark' ? 'bg-lime-400 text-slate-950 hover:bg-lime-300' : 'bg-emerald-500 text-white hover:bg-emerald-600'}`}
                  >
                    Lookup Ticket
                  </button>
                </div>



                {ticketResult && (
                  <div className={`rounded-xl border p-4 text-xs font-medium transition ${theme === 'dark' ? 'border-slate-800 bg-slate-950 text-slate-300' : 'border-slate-200 bg-slate-50 text-slate-650'}`}>
                    ℹ️ {ticketResult}
                  </div>
                )}

                {/* PREMIUM TICKET VISUALIZER CARD */}
                {ticketDetails && (
                  <div className={`overflow-hidden rounded-2xl border shadow-lg transition ${theme === 'dark' ? 'border-slate-800 bg-slate-950' : 'border-slate-200 bg-white'}`}>
                    <div className={`border-b p-4 flex items-center justify-between transition ${theme === 'dark' ? 'border-slate-850 bg-slate-900/40' : 'border-slate-100 bg-slate-50/50'}`}>
                      <div>
                        <span className={`text-[10px] font-bold uppercase ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>SYSINCIDENT LEDGER</span>
                        <h4 className={`text-md font-bold mt-0.5 ${theme === 'dark' ? 'text-slate-100' : 'text-slate-900'}`}>{ticketDetails.number}</h4>
                      </div>
                      <span className={`rounded-full px-3 py-0.5 text-[10px] font-bold uppercase ${ticketDetails.state === 'Closed' ? (theme === 'dark' ? 'bg-slate-800 text-slate-400' : 'bg-slate-200 text-slate-600') : 'bg-amber-400/10 text-amber-505 border border-amber-400/20'}`}>
                        {ticketDetails.state}
                      </span>
                    </div>

                    <div className="p-4 space-y-3.5 text-xs">
                      <div className="grid gap-2 grid-cols-2">
                        <div className={`p-2.5 rounded-xl border transition ${theme === 'dark' ? 'bg-slate-900/30 border-slate-800/80' : 'bg-slate-50 border-slate-200'}`}>
                          <p className={`text-[9px] uppercase tracking-wider font-bold ${theme === 'dark' ? 'text-slate-500' : 'text-slate-450'}`}>Severity Matrix</p>
                          <p className={`mt-1 font-semibold ${theme === 'dark' ? 'text-slate-200' : 'text-slate-800'}`}>{ticketDetails.severity}</p>
                        </div>
                        <div className={`p-2.5 rounded-xl border transition ${theme === 'dark' ? 'bg-slate-900/30 border-slate-800/80' : 'bg-slate-50 border-slate-200'}`}>
                          <p className={`text-[9px] uppercase tracking-wider font-bold ${theme === 'dark' ? 'text-slate-500' : 'text-slate-450'}`}>SRE Owner</p>
                          <p className={`mt-1 font-semibold ${theme === 'dark' ? 'text-slate-200' : 'text-slate-800'}`}>{ticketDetails.assigned_to || 'Unassigned'}</p>
                        </div>
                      </div>

                      <div className={`p-3 rounded-xl border transition ${theme === 'dark' ? 'bg-slate-900/30 border-slate-800/80' : 'bg-slate-50 border-slate-200'}`}>
                        <p className={`text-[9px] uppercase tracking-wider font-bold ${theme === 'dark' ? 'text-slate-500' : 'text-slate-450'}`}>Short Description</p>
                        <p className={`mt-1 font-medium ${theme === 'dark' ? 'text-slate-100' : 'text-slate-850'}`}>{ticketDetails.short_description}</p>
                      </div>

                      <div className={`p-3 rounded-xl border transition ${theme === 'dark' ? 'bg-slate-900/30 border-slate-800/80' : 'bg-slate-50 border-slate-200'}`}>
                        <p className={`text-[9px] uppercase tracking-wider font-bold ${theme === 'dark' ? 'text-slate-500' : 'text-slate-450'}`}>RCA Summary close notes</p>
                        <p className={`mt-1 font-mono text-[11px] leading-4 italic ${theme === 'dark' ? 'text-slate-300' : 'text-slate-650'}`}>
                          "{ticketDetails.close_notes || 'Ticket is actively being investigated. Resolution notes will populate upon closure.'}"
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* 4. PLUGIN MARKETPLACE */}
            {activeSection === 'marketplace' && (
              <section className={`rounded-3xl border p-5 shadow-2xl backdrop-blur-xl transition-all duration-300 ${theme === 'dark' ? 'border-slate-800/80 bg-slate-900/35' : 'border-slate-200 bg-white'}`}>
                <h2 className={`text-xl font-black ${theme === 'dark' ? 'text-slate-50' : 'text-slate-900'}`}>Local Plugins Registry</h2>
                <p className={`mt-1 text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Hot-load or disable agents seamlessly without core system rebuilds.</p>
                
                <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {availableAgents
                    .filter(ag => ag.id !== 'auto')
                    .map((ag) => {
                      const agentDescriptions: Record<string, { desc: string, tag: string }> = {
                        log_analysis_agent: { desc: 'Parses txt, json, and evtx log structures to extract diagnostics.', tag: '📁 system' },
                        servicenow_agent: { desc: 'Adapts REST endpoints offline to search tickets and extract RCA.', tag: '🎫 itsm' },
                        github_actions_agent: { desc: 'Analyses pipeline workflows logs to suggest runner repairs.', tag: '⚙️ cicd' },
                        terraform_agent: { desc: 'Validates plan structures against configuration guardrails.', tag: '🛠️ infra' },
                        ansible_agent: { desc: 'Automates playbook dry-runs and checks node availability.', tag: '⚡ automation' },
                        monitoring_agent: { desc: 'Reviews hypervisor capacity maps, processes disk and memory alerts.', tag: '📊 monitoring' },
                        vmware_agent: { desc: 'Scans hypervisors performance maps and detects over-allocation.', tag: '💾 vms' },
                        nutanix_agent: { desc: 'Reviews Nutanix HCI clusters, storage pools, and hypervisor allocations.', tag: '🚀 hci' }
                      };
                      const metadata = agentDescriptions[ag.id] || { desc: (ag as any).description || 'Custom local agent plugin.', tag: '⚙️ agent' };
                      
                      return (
                        <div key={ag.id} className={`flex flex-col justify-between rounded-2xl border p-4 text-xs transition ${theme === 'dark' ? 'border-slate-800 bg-slate-950' : 'border-slate-200 bg-slate-50'}`}>
                          <div>
                            <div className="flex items-center justify-between gap-2">
                              <span className={`text-[9px] font-bold uppercase tracking-wider ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>{metadata.tag}</span>
                              <span className={`h-1.5 w-1.5 rounded-full ${ag.enabled ? (theme === 'dark' ? 'bg-lime-400 animate-pulse' : 'bg-emerald-500') : 'bg-slate-400'}`} />
                            </div>
                            <p className={`mt-2 font-bold text-sm ${theme === 'dark' ? 'text-slate-100' : 'text-slate-900'}`}>{ag.name}</p>
                            <p className={`mt-1.5 leading-4 ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>{metadata.desc}</p>
                          </div>
                          
                          <button
                            type="button"
                            onClick={() => toggleAgent(ag.id, !!ag.enabled)}
                            className={`mt-4 rounded-xl px-4 py-1.5 text-[10px] font-bold uppercase border transition w-full ${ag.enabled ? (theme === 'dark' ? 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800' : 'bg-slate-200 border-slate-300 text-slate-650 hover:bg-slate-300') : (theme === 'dark' ? 'bg-lime-400 border-transparent text-slate-950 hover:bg-lime-300' : 'bg-emerald-500 border-transparent text-white hover:bg-emerald-600')}`}
                          >
                            {ag.enabled ? 'Enabled' : 'Deploy Plugin'}
                          </button>
                        </div>
                      );
                    })}
                </div>
              </section>
            )}

            {/* 5. CONFIG AND TUNING */}
            {activeSection === 'settings' && (
              <section className={`rounded-3xl border p-5 shadow-2xl backdrop-blur-xl transition-all duration-300 ${theme === 'dark' ? 'border-slate-800/80 bg-slate-900/35' : 'border-slate-200 bg-white'}`}>
                <h2 className={`text-xl font-black ${theme === 'dark' ? 'text-slate-50' : 'text-slate-900'}`}>Local System Parameters</h2>
                <p className={`mt-1 text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Configure parameters, local folders settings, and model context thresholds.</p>
                <div className="mt-4 grid gap-4 sm:grid-cols-2 text-xs">
                  <div className={`rounded-2xl border p-4 transition ${theme === 'dark' ? 'border-slate-800 bg-slate-950' : 'border-slate-200 bg-slate-50'}`}>
                    <p className={`font-bold ${theme === 'dark' ? 'text-slate-200' : 'text-slate-800'}`}>Local GGUF Model settings</p>
                    <div className={`mt-2 space-y-1.5 font-mono text-[10px] ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      <p>Path: backend/models/qwen2.5-1.5b-instruct-gguf/model.gguf</p>
                      <p>Threads limit: 4</p>
                      <p>Context window: 2048 tokens</p>
                      <p>Temperature bias: 0.15</p>
                    </div>
                  </div>
                  <div className={`rounded-2xl border p-4 transition ${theme === 'dark' ? 'border-slate-800 bg-slate-950' : 'border-slate-200 bg-slate-50'}`}>
                    <p className={`font-bold ${theme === 'dark' ? 'text-slate-200' : 'text-slate-800'}`}>Relational SQLite Memory</p>
                    <div className={`mt-2 space-y-1.5 font-mono text-[10px] ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      <p>Database: backend/app.db</p>
                      <p>Adapter: SQLAlchemy scoped sessions</p>
                      <p>Cascade rules: ON DELETE CASCADE</p>
                      <p>Metadata indexing: UUID</p>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* 6. ADMIN SYSTEM METRICS */}
            {activeSection === 'admin' && (
              <section className={`rounded-3xl border p-5 shadow-2xl backdrop-blur-xl transition-all duration-300 ${theme === 'dark' ? 'border-slate-800/80 bg-slate-900/35' : 'border-slate-200 bg-white'}`}>
                <h2 className={`text-xl font-black ${theme === 'dark' ? 'text-slate-50' : 'text-slate-900'}`}>System Governance Panel</h2>
                <p className={`mt-1 text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-550'}`}>Check agents health, monitor active processes, and scan compliance logs.</p>
                
                <div className="mt-4 space-y-3 text-xs">
                  <div className="grid gap-3 grid-cols-3">
                    {availableAgents.map((ag) => (
                      <div key={ag.id} className={`rounded-2xl border p-4 transition ${theme === 'dark' ? 'border-slate-800 bg-slate-950' : 'border-slate-200 bg-slate-50'}`}>
                        <p className={`font-bold ${theme === 'dark' ? 'text-slate-200' : 'text-slate-800'}`}>{ag.name}</p>
                        <div className="mt-2 space-y-1 text-[10px] font-mono text-slate-500">
                          <p>ID: {ag.id}</p>
                          <p>Version: {ag.version ?? '1.0.0'}</p>
                          <p>Lifecycle: `Active`</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {(agentError || pluginError) && (
                    <div className="rounded-xl border border-amber-500/10 bg-amber-500/5 p-3 text-amber-400 text-[11px] font-mono">
                      ⚠️ Platform warning: {agentError ?? pluginError}
                    </div>
                  )}
                </div>
              </section>
            )}

          </main>
        </div>
      </div>
    </div>
  );
}

export default App;
