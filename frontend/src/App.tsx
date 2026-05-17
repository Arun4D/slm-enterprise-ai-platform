import { useEffect, useMemo, useState, type ChangeEvent } from 'react';

const sections = [
  { id: 'chat', label: 'Chat' },
  { id: 'marketplace', label: 'Plugin Marketplace' },
  { id: 'logs', label: 'Log Analysis' },
  { id: 'snow', label: 'SNOW Ticket Lookup' },
  { id: 'settings', label: 'Settings' },
  { id: 'admin', label: 'Admin' },
  { id: 'login', label: 'Login' }
] as const;

type Section = (typeof sections)[number]['id'];

type Message = {
  role: 'user' | 'assistant' | 'system';
  text: string;
  logResult?: LogAnalysisResult;
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
    text: 'You are SLM Enterprise Assistant. Use local agents to answer user requests.'
  }
];

const fallbackAgents: Agent[] = [
  { id: 'log_analysis_agent', name: 'Log Analysis Agent' },
  { id: 'snownet', name: 'ServiceNow Agent' },
  { id: 'terraform', name: 'Terraform Agent' }
];

function LogAnalysisCard({ result, compact = false }: { result: LogAnalysisResult; compact?: boolean }) {
  const classified = result.classified_entries ?? {};
  const errorCount = classified.errors?.length ?? 0;
  const warningCount = classified.warnings?.length ?? 0;
  const infoCount = classified.info?.length ?? 0;
  const patterns = result.patterns ?? [];
  const appStatus = result.application_status;
  const isClean = errorCount === 0 && warningCount === 0;

  return (
    <div className={`${compact ? 'mt-3' : 'mt-4'} overflow-hidden rounded-2xl border border-slate-700/70 bg-slate-950/70 text-sm shadow-soft`}>
      <div className="border-b border-slate-800 bg-slate-900/80 px-5 py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Log Analysis</p>
            <h3 className="mt-1 text-lg font-semibold text-slate-50">
              {result.query_answer ?? (isClean ? 'No actionable issues found' : `${errorCount} errors and ${warningCount} warnings found`)}
            </h3>
            <p className="mt-1 text-slate-400">Explicit log levels are evaluated before message text.</p>
          </div>
          <span className={`w-fit rounded-full px-3 py-1 text-xs font-semibold ${isClean ? 'bg-emerald-500/15 text-emerald-300' : 'bg-red-500/15 text-red-300'}`}>
            {isClean ? 'Clean' : 'Needs review'}
          </span>
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div className="grid gap-3 sm:grid-cols-5">
          {[
            ['Files', result.files_analyzed ?? 0],
            ['Entries', result.total_entries ?? 0],
            ['Errors', errorCount],
            ['Warnings', warningCount],
            ['Info', infoCount]
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
              <p className="mt-2 text-2xl font-semibold text-slate-50">{value}</p>
            </div>
          ))}
        </div>

        {appStatus && (
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-100">
                  {appStatus.application_started ? 'Application started successfully' : 'Startup completion not detected'}
                </p>
                <p className="mt-1 text-slate-400">
                  {appStatus.application_name ?? 'Application'}
                  {appStatus.startup_seconds != null ? ` in ${appStatus.startup_seconds} seconds` : ''}
                  {appStatus.port != null ? ` on port ${appStatus.port}` : ''}
                  {appStatus.pid != null ? `, PID ${appStatus.pid}` : ''}
                </p>
              </div>
              <span className="w-fit rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
                {result.classifier_version ?? 'classifier unknown'}
              </span>
            </div>
          </div>
        )}

        {patterns.length > 0 ? (
          <div>
            <div className="mb-3 flex items-center justify-between">
              <p className="font-semibold text-slate-100">Actionable Patterns</p>
              <span className="text-xs text-slate-500">{patterns.length} detected</span>
            </div>
            <div className="space-y-2">
              {patterns.slice(0, 5).map((pattern, index) => (
                <div key={`${pattern.pattern}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${pattern.level === 'ERROR' ? 'bg-red-500/15 text-red-300' : 'bg-amber-500/15 text-amber-300'}`}>
                      {pattern.level ?? 'ISSUE'}
                    </span>
                    <span className="text-xs text-slate-400">{pattern.count} occurrence{pattern.count === 1 ? '' : 's'}</span>
                  </div>
                  <p className="mt-2 break-words font-mono text-xs leading-5 text-slate-300">{pattern.pattern}</p>
                  {pattern.samples?.[0] && (
                    <p className="mt-2 border-l border-slate-700 pl-3 text-xs leading-5 text-slate-400">{pattern.samples[0]}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-emerald-200">
            No error or warning patterns were detected.
          </div>
        )}

        {(result.errors?.length ?? 0) > 0 && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-amber-200">
            {result.errors?.map((error, index) => (
              <p key={`${error.file ?? 'processing'}-${index}`}>{error.file ?? 'Processing'}: {error.error ?? 'Unknown error'}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function RichText({ text }: { text: string }) {
  const lines = text.split('\n').filter((line) => line.trim().length > 0);

  return (
    <div className="space-y-2 leading-7 text-slate-200">
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (trimmed.startsWith('### ')) {
          return <h4 key={index} className="pt-2 text-base font-semibold text-slate-50">{trimmed.replace(/^###\s+/, '')}</h4>;
        }
        if (trimmed.startsWith('## ')) {
          return <h3 key={index} className="text-lg font-semibold text-slate-50">{trimmed.replace(/^##\s+/, '')}</h3>;
        }
        if (trimmed.startsWith('- ')) {
          return <p key={index} className="pl-4 text-slate-300 before:mr-2 before:text-slate-500 before:content-['•']">{trimmed.slice(2)}</p>;
        }
        if (/^\d+\.\s/.test(trimmed)) {
          return <p key={index} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 font-mono text-xs leading-5 text-slate-300">{trimmed}</p>;
        }
        return <p key={index} className="text-slate-300">{trimmed.replace(/`/g, '')}</p>;
      })}
    </div>
  );
}

function MessageContent({ message }: { message: Message }) {
  if (message.logResult) {
    return <LogAnalysisCard result={message.logResult} compact />;
  }

  return <RichText text={message.text} />;
}

function App() {
  const [activeSection, setActiveSection] = useState<Section>('chat');
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [draft, setDraft] = useState('');
  const [availableAgents, setAvailableAgents] = useState<Agent[]>(fallbackAgents);
  const [selectedAgent, setSelectedAgent] = useState(fallbackAgents[0].id);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [folderFiles, setFolderFiles] = useState<File[]>([]);
  const [folderPaths, setFolderPaths] = useState<string[]>([]);
  const [ticketId, setTicketId] = useState('IT-12345');
  const [ticketResult, setTicketResult] = useState<string | null>(null);
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [pluginError, setPluginError] = useState<string | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [logResult, setLogResult] = useState<LogAnalysisResult | string | null>(null);
  const [isAnalyzingLogs, setIsAnalyzingLogs] = useState(false);

  const currentAgent = useMemo(
    () => availableAgents.find((agent) => agent.id === selectedAgent),
    [selectedAgent]
  );

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch('/api/v1/agents');
        if (!response.ok) {
          throw new Error(`Failed to load agents: ${response.statusText}`);
        }

        const data = await response.json();
        const loadedAgents = (data.agents ?? []) as Agent[];
        if (loadedAgents.length > 0) {
          setAvailableAgents(loadedAgents);
          setSelectedAgent((current) =>
            loadedAgents.some((agent) => agent.id === current) ? current : loadedAgents[0].id
          );
        }
      } catch (error) {
        setAgentError(error instanceof Error ? error.message : 'Unknown error');
      }
    };

    const fetchPlugins = async () => {
      try {
        const response = await fetch('/api/v1/plugins');
        if (!response.ok) {
          throw new Error(`Failed to load plugins: ${response.statusText}`);
        }

        const data = await response.json();
        setPlugins(data.plugins ?? []);
      } catch (error) {
        setPluginError(error instanceof Error ? error.message : 'Unknown error');
      }
    };

    fetchAgents();
    fetchPlugins();
  }, []);

  const sendMessage = async () => {
    if (!draft.trim()) return;

    const userMessage: Message = { role: 'user', text: draft.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setDraft('');

    try {
      if (selectedAgent === 'log_analysis_agent' && attachments.length > 0) {
        const formData = new FormData();
        formData.append('intent', userMessage.text);
        attachments.forEach((file) => {
          formData.append('files', file, file.name);
        });

        const response = await fetch('/api/v1/agents/log_analysis_agent/analyze-files', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          const error = await response.json().catch(() => null);
          throw new Error(error?.detail ?? `Log analysis failed: ${response.statusText}`);
        }

        const data = await response.json();
        const result = data.result ?? {};
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            text: result.summary ?? JSON.stringify(result, null, 2),
            logResult: result
          }
        ]);
        setAttachments([]);
        return;
      }

      const response = await fetch(`/api/v1/agents/${selectedAgent}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: selectedAgent,
          input_data: {
            intent: userMessage.text
          }
        })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail ?? `Agent call failed: ${response.statusText}`);
      }

      const data = await response.json();
      const summary = data.result?.summary ?? JSON.stringify(data.result ?? {}, null, 2);
      const result = data.result as LogAnalysisResult | undefined;
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: summary,
          logResult: result?.classified_entries || result?.application_status ? result : undefined
        }
      ]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Unknown backend error';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `${currentAgent?.name ?? 'Selected agent'} could not complete this request.\n\n${detail}`
        }
      ]);
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
      setLogResult('Choose a folder with .log, .txt, .json, .jsonl, or .evtx files first.');
      return;
    }

    setIsAnalyzingLogs(true);
    setLogResult(null);

    const formData = new FormData();
    formData.append('intent', 'analyze logs from selected folder');
    folderFiles.forEach((file) => {
      formData.append('files', file, file.webkitRelativePath || file.name);
    });

    try {
      const response = await fetch('/api/v1/agents/log_analysis_agent/analyze-files', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail ?? `Log analysis failed: ${response.statusText}`);
      }

      const data = await response.json();
      const result = data.result ?? {};
      setLogResult(result);
    } catch (error) {
      setLogResult(error instanceof Error ? error.message : 'Unknown log analysis error');
    } finally {
      setIsAnalyzingLogs(false);
    }
  };

  const lookupTicket = () => {
    setTicketResult(`Ticket ${ticketId} is currently in "In Progress" status and has a high priority impact on production.`);
  };

  const renderLogResult = () => {
    if (!logResult) return null;

    if (typeof logResult === 'string') {
      return (
        <div className="mt-4 whitespace-pre-wrap rounded-3xl border border-slate-800 bg-slate-950/80 p-5 text-sm text-slate-200">
          {logResult}
        </div>
      );
    }

    return <LogAnalysisCard result={logResult} />;
  };

  return (
    <div className={theme === 'dark' ? 'min-h-screen bg-slate-950 text-slate-100' : 'min-h-screen bg-slate-100 text-slate-900'}>
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-4 sm:px-6 lg:px-8">
        <header className="mb-4 flex items-center justify-between rounded-3xl border border-slate-800/70 bg-slate-900/80 px-6 py-4 shadow-soft backdrop-blur-xl sm:px-8">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-400">SLM Enterprise AI Platform</p>
            <h1 className="mt-1 text-3xl font-semibold">ChatGPT-Style Operations Console</h1>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-2xl bg-slate-700 px-4 py-2 text-sm transition hover:bg-slate-600"
              onClick={() => setTheme((value) => (value === 'dark' ? 'light' : 'dark'))}
            >
              {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
            </button>
            <div className="rounded-2xl bg-slate-800/80 px-4 py-2 text-sm">Operator</div>
          </div>
        </header>

        <div className="grid flex-1 gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="rounded-3xl border border-slate-800/70 bg-slate-900/70 p-4 shadow-soft backdrop-blur-xl">
            <nav className="space-y-2">
              {sections.map((section) => (
                <button
                  key={section.id}
                  type="button"
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full rounded-2xl px-4 py-3 text-left text-sm transition ${activeSection === section.id ? 'bg-accent/20 text-accent' : 'text-slate-300 hover:bg-slate-800/70'}`}
                >
                  {section.label}
                </button>
              ))}
            </nav>

            <div className="mt-6 rounded-3xl border border-slate-800/80 bg-slate-950/70 p-4 text-sm text-slate-400">
              <p className="font-semibold text-slate-200">Platform highlights</p>
              <ul className="mt-3 space-y-2">
                <li>Local SLM orchestration</li>
                <li>Plugin marketplace</li>
                <li>Agent routing</li>
                <li>Secure operations UI</li>
              </ul>
            </div>
          </aside>

          <main className="space-y-6">
            {activeSection === 'chat' && (
              <section className="rounded-3xl border border-slate-800/70 bg-slate-900/70 p-6 shadow-soft backdrop-blur-xl">
                <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold">Streaming Chat</h2>
                    <p className="mt-2 text-sm text-slate-400">Interact with agents, upload files, and monitor conversations in real time.</p>
                  </div>

                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                    <label className="flex items-center gap-3 rounded-2xl border border-slate-700/80 bg-slate-950/70 px-4 py-3">
                      <span className="text-sm text-slate-400">Agent</span>
                      <select
                        value={selectedAgent}
                        onChange={(event) => setSelectedAgent(event.target.value)}
                        className="bg-transparent text-sm text-slate-100 outline-none"
                      >
                        {availableAgents.map((agent) => (
                          <option key={agent.id} value={agent.id}>{agent.name}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                </div>

                <div className="mb-6 space-y-4 rounded-3xl border border-slate-800/60 bg-slate-950/90 p-4">
                  {messages.map((message, index) => (
                    <div
                      key={`${message.role}-${index}`}
                      className={`rounded-2xl p-4 ${
                        message.role === 'assistant'
                          ? 'border border-slate-800 bg-slate-900/60'
                          : message.role === 'user'
                            ? 'ml-auto max-w-3xl bg-slate-700/80'
                            : 'max-w-4xl border border-slate-800 bg-slate-900/80'
                      } ${message.role === 'assistant' ? 'max-w-5xl' : ''} text-sm`}
                    >
                      <div className="mb-1 text-xs uppercase tracking-[0.3em] text-slate-400">{message.role}</div>
                      <MessageContent message={message} />
                    </div>
                  ))}
                </div>

                <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
                  <div className="rounded-3xl border border-slate-800/60 bg-slate-950/80 p-4">
                    <textarea
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      placeholder="Ask a question, request a log analysis, or route a task to an agent..."
                      className="min-h-[160px] w-full resize-none rounded-3xl border border-slate-800/80 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none focus:border-accent/80"
                    />
                    <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <label className="flex items-center gap-2 text-sm text-slate-400">
                        <input type="file" multiple onChange={handleFiles} className="hidden" />
                        <span className="cursor-pointer rounded-full border border-slate-700/90 px-3 py-2 text-slate-300 hover:bg-slate-800/70">Upload files</span>
                      </label>
                      <button
                        type="button"
                        onClick={sendMessage}
                        className="rounded-full bg-accent px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-lime-400"
                      >
                        Send
                      </button>
                    </div>
                    {attachments.length > 0 && (
                      <p className="mt-3 text-xs text-slate-400">Attached files: {attachments.map((file) => file.name).join(', ')}</p>
                    )}
                  </div>

                  <div className="space-y-4 rounded-3xl border border-slate-800/60 bg-slate-950/80 p-4">
                    <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-4 text-sm text-slate-300">
                      <p className="font-semibold text-slate-100">Session Summary</p>
                      <p className="mt-3 text-sm leading-6 text-slate-400">This workspace connects chat, log analysis, SNOW lookup, and admin controls under a secure internal operations experience.</p>
                    </div>
                    <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-4 text-sm text-slate-300">
                      <p className="font-semibold text-slate-100">Selected folder scan</p>
                      <p className="mt-2 text-slate-400">Use the log analysis section to choose a folder from your workstation and inspect logs securely.</p>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {activeSection === 'marketplace' && (
              <section className="rounded-3xl border border-slate-800/70 bg-slate-900/70 p-6 shadow-soft backdrop-blur-xl">
                <h2 className="text-2xl font-semibold">Dynamic Plugin Marketplace</h2>
                <p className="mt-2 text-sm text-slate-400">Discover and enable platform agents and plugins for log analysis, monitoring, incident response, and infrastructure automation.</p>
                <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {['Log Analysis', 'ServiceNow', 'GitHub Actions', 'Terraform', 'Monitoring', 'Ansible'].map((item) => (
                    <div key={item} className="rounded-3xl border border-slate-800 bg-slate-950/80 p-5">
                      <p className="font-semibold text-slate-100">{item} Agent</p>
                      <p className="mt-2 text-sm text-slate-400">Enable this plugin to connect the platform to operational workflows and route tasks automatically.</p>
                      <button type="button" className="mt-4 rounded-2xl bg-slate-800 px-4 py-2 text-sm text-slate-100 transition hover:bg-slate-700">View details</button>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {activeSection === 'logs' && (
              <section className="rounded-3xl border border-slate-800/70 bg-slate-900/70 p-6 shadow-soft backdrop-blur-xl">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold">Folder Picker for Log Analysis</h2>
                    <p className="mt-2 text-sm text-slate-400">Select a directory of log files to inspect and send to the Log Analysis Agent.</p>
                  </div>
                  <label className="rounded-2xl border border-slate-700/80 bg-slate-950/80 px-4 py-3 text-sm text-slate-200 cursor-pointer hover:bg-slate-800/70">
                    Choose folder
                    {/* @ts-ignore */}
                    <input type="file" webkitdirectory="true" directory={true as any} multiple className="hidden" onChange={handleFolder} />
                  </label>
                </div>
                <div className="mt-6 grid gap-4 rounded-3xl border border-slate-800 bg-slate-950/70 p-4">
                  {folderPaths.length === 0 ? (
                    <p className="text-sm text-slate-400">No folder selected yet.</p>
                  ) : (
                    <div className="space-y-2 text-sm text-slate-200">
                      <p className="font-medium">Selected files</p>
                      <ul className="space-y-1 text-slate-400">
                        {folderPaths.map((path) => (
                          <li key={path} className="truncate">{path}</li>
                        ))}
                      </ul>
                      <button
                        type="button"
                        onClick={analyzeSelectedLogs}
                        disabled={isAnalyzingLogs}
                        className="mt-4 rounded-full bg-accent px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-lime-400 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isAnalyzingLogs ? 'Analyzing...' : 'Analyze with backend'}
                      </button>
                    </div>
                  )}
                </div>
                {renderLogResult()}
              </section>
            )}

            {activeSection === 'snow' && (
              <section className="rounded-3xl border border-slate-800/70 bg-slate-900/70 p-6 shadow-soft backdrop-blur-xl">
                <h2 className="text-2xl font-semibold">ServiceNow Ticket Lookup</h2>
                <p className="mt-2 text-sm text-slate-400">Query incident tickets and retrieve the latest resolution status from your internal ITSM workflow.</p>
                <div className="mt-6 grid gap-4 sm:grid-cols-[1fr_180px]">
                  <input
                    type="text"
                    value={ticketId}
                    onChange={(event) => setTicketId(event.target.value)}
                    className="rounded-3xl border border-slate-800/80 bg-slate-950/80 px-4 py-3 text-sm text-slate-100 outline-none focus:border-accent/80"
                    placeholder="Enter ticket ID"
                  />
                  <button onClick={lookupTicket} className="rounded-3xl bg-accent px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-lime-400">Lookup</button>
                </div>
                {ticketResult && (
                  <div className="mt-6 rounded-3xl border border-slate-800 bg-slate-950/80 p-5 text-sm text-slate-200">
                    {ticketResult}
                  </div>
                )}
              </section>
            )}

            {activeSection === 'settings' && (
              <section className="rounded-3xl border border-slate-800/70 bg-slate-900/70 p-6 shadow-soft backdrop-blur-xl">
                <h2 className="text-2xl font-semibold">Settings</h2>
                <p className="mt-2 text-sm text-slate-400">Configure platform behavior, security controls, and agent preferences.</p>
                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-5">
                    <p className="font-semibold text-slate-100">Theme</p>
                    <p className="mt-2 text-slate-400">Use the top-right toggle to switch between light and dark modes.</p>
                  </div>
                  <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-5">
                    <p className="font-semibold text-slate-100">Agent routing</p>
                    <p className="mt-2 text-slate-400">Assign primary agents for log analysis, incident management, and infrastructure tasks.</p>
                  </div>
                </div>
              </section>
            )}

            {activeSection === 'admin' && (
              <section className="rounded-3xl border border-slate-800/70 bg-slate-900/70 p-6 shadow-soft backdrop-blur-xl">
                <h2 className="text-2xl font-semibold">Admin Console</h2>
                <p className="mt-2 text-sm text-slate-400">Manage agents, review status, and enable or disable plugins.</p>
                <div className="mt-6 rounded-3xl border border-slate-800 bg-slate-950/80 p-5 text-sm text-slate-200">
                  <div className="grid gap-3 sm:grid-cols-3">
                    {availableAgents.map((agent) => (
                      <div key={agent.id} className="rounded-3xl border border-slate-800 bg-slate-900/80 p-4">
                        <p className="font-semibold text-slate-100">{agent.name}</p>
                        <p className="mt-2 text-slate-400">Version {agent.version ?? '0.1.0'}</p>
                        <p className="mt-1 text-slate-400">Status {agent.status ?? 'unknown'}</p>
                        <button type="button" className="mt-4 inline-flex rounded-full bg-accent px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-lime-400">Enable</button>
                      </div>
                    ))}
                  </div>
                  {(agentError || pluginError) && (
                    <p className="mt-4 text-sm text-amber-300">
                      {agentError ?? pluginError}
                    </p>
                  )}
                </div>
              </section>
            )}

            {activeSection === 'login' && (
              <section className="rounded-3xl border border-slate-800/70 bg-slate-900/70 p-6 shadow-soft backdrop-blur-xl">
                <h2 className="text-2xl font-semibold">Secure Login</h2>
                <p className="mt-2 text-sm text-slate-400">Placeholder for authentication and role-based access control.</p>
                <div className="mt-6 space-y-4 rounded-3xl border border-slate-800 bg-slate-950/80 p-6">
                  <div className="grid gap-3">
                    <input className="rounded-3xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none" placeholder="Username" />
                    <input type="password" className="rounded-3xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none" placeholder="Password" />
                  </div>
                  <button type="button" className="w-full rounded-3xl bg-accent px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-lime-400">Sign in</button>
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
