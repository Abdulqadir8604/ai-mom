import { useState, useEffect, useRef } from "react";

const sections = [
  { id: "getting-started", label: "Getting Started" },
  { id: "processing-meeting", label: "Processing a Meeting" },
  { id: "speaker-diarization", label: "Speaker Diarization" },
  { id: "speaker-enrollment", label: "Speaker Enrollment" },
  { id: "language-support", label: "Language Support" },
  { id: "model-selection", label: "Model Selection Guide" },
  { id: "understanding-minutes", label: "Understanding Your Minutes" },
  { id: "diarization-caching", label: "Diarization Caching" },
  { id: "tips-tricks", label: "Tips & Tricks" },
  { id: "api-keys", label: "API Keys & Configuration" },
];

function TipBox({ children }) {
  return (
    <div className="flex gap-3 bg-blue-950/40 border border-blue-800/50 rounded-lg px-4 py-3 my-4">
      <span className="text-blue-400 text-base mt-0.5 shrink-0">ℹ️</span>
      <p className="text-blue-200 text-sm leading-relaxed">{children}</p>
    </div>
  );
}

function WarnBox({ children }) {
  return (
    <div className="flex gap-3 bg-amber-950/40 border border-amber-700/50 rounded-lg px-4 py-3 my-4">
      <span className="text-amber-400 text-base mt-0.5 shrink-0">⚠️</span>
      <p className="text-amber-200 text-sm leading-relaxed">{children}</p>
    </div>
  );
}

function Code({ children }) {
  return (
    <code className="bg-gray-900 border border-gray-700 rounded px-1.5 py-0.5 text-xs font-mono text-green-400">
      {children}
    </code>
  );
}

function CodeBlock({ children }) {
  return (
    <pre className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 my-3 text-xs font-mono text-green-400 overflow-x-auto leading-relaxed">
      {children}
    </pre>
  );
}

function SectionHeading({ id, children }) {
  return (
    <h2
      id={id}
      className="text-xl font-bold text-white mt-10 mb-4 pb-2 border-b border-gray-800 scroll-mt-6"
    >
      {children}
    </h2>
  );
}

function SubHeading({ children }) {
  return (
    <h3 className="text-base font-semibold text-gray-200 mt-6 mb-2">
      {children}
    </h3>
  );
}

function Prose({ children }) {
  return (
    <p className="text-gray-300 text-sm leading-relaxed mb-3">{children}</p>
  );
}

function BulletList({ items }) {
  return (
    <ul className="space-y-1.5 mb-4">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2 text-sm text-gray-300">
          <span className="text-primary mt-0.5 shrink-0">•</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function Docs() {
  const [activeSection, setActiveSection] = useState("getting-started");
  const contentRef = useRef(null);
  const observerRef = useRef(null);

  useEffect(() => {
    const options = {
      root: contentRef.current,
      rootMargin: "0px 0px -60% 0px",
      threshold: 0,
    };

    observerRef.current = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          setActiveSection(entry.target.id);
        }
      });
    }, options);

    sections.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observerRef.current.observe(el);
    });

    return () => observerRef.current?.disconnect();
  }, []);

  const scrollTo = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 sticky top-0 h-screen overflow-y-auto border-r border-gray-800 bg-surface/50 py-6 px-3 hidden md:block">
        <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 px-3 mb-3">
          Contents
        </p>
        <nav className="space-y-0.5">
          {sections.map((s) => (
            <button
              key={s.id}
              onClick={() => scrollTo(s.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                activeSection === s.id
                  ? "bg-primary/20 text-primary"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {s.label}
            </button>
          ))}
        </nav>
      </aside>

      {/* Content */}
      <div
        ref={contentRef}
        className="flex-1 overflow-y-auto"
      >
        <div className="max-w-3xl mx-auto px-8 py-8">
          {/* Page header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-white">Documentation</h1>
            <p className="text-gray-400 text-sm mt-1">
              Everything you need to know about using AI MOM
            </p>
          </div>

          {/* ── Getting Started ─────────────────────────────────────── */}
          <SectionHeading id="getting-started">Getting Started</SectionHeading>

          <SubHeading>What is AI MOM?</SubHeading>
          <Prose>
            AI MOM (AI Meeting Minutes) is an AI-powered tool that turns audio
            recordings into structured meeting minutes. Upload a recording, choose
            your settings, and the system handles transcription, speaker
            identification, and AI summarization — producing a clean document with
            a session summary, key decisions, action items, next steps, and a
            full attributed transcript.
          </Prose>

          <SubHeading>Quick Start</SubHeading>
          <ol className="space-y-2 mb-4">
            {[
              "Go to the Dashboard and drag-and-drop (or browse for) your audio file.",
              "Set a Title so you can find the minutes later.",
              "Choose the Language that matches your recording.",
              "Pick a Model — Small is a good default for most meetings.",
              "Toggle Diarize Speakers if you want the transcript attributed to individual speakers.",
              'Click "Process Meeting" and wait for the job to complete.',
              "Click View Minutes once the job shows Done.",
            ].map((step, i) => (
              <li key={i} className="flex gap-3 text-sm text-gray-300">
                <span className="bg-primary/20 text-primary text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>

          {/* ── Processing a Meeting ────────────────────────────────── */}
          <SectionHeading id="processing-meeting">Processing a Meeting</SectionHeading>

          <SubHeading>Uploading Audio</SubHeading>
          <Prose>
            Drop your file onto the upload zone on the Dashboard, or click it to
            open a file browser. Supported formats: <Code>WAV</Code>,{" "}
            <Code>MP3</Code>, <Code>M4A</Code>, <Code>FLAC</Code>,{" "}
            <Code>OGG</Code>. There is no hard size limit, but larger files take
            longer to process.
          </Prose>

          <SubHeading>Settings Explained</SubHeading>

          <div className="space-y-4 mb-4">
            <div className="bg-surface rounded-lg border border-gray-800 px-4 py-3">
              <p className="text-sm font-semibold text-white mb-1">Title</p>
              <p className="text-sm text-gray-400">
                A human-readable name for this recording. If left blank the
                filename is used. Helps you identify the meeting in the jobs
                list.
              </p>
            </div>

            <div className="bg-surface rounded-lg border border-gray-800 px-4 py-3">
              <p className="text-sm font-semibold text-white mb-1">Language</p>
              <p className="text-sm text-gray-400">
                Controls how Whisper interprets the audio. Choose{" "}
                <Code>English</Code> for English-only meetings,{" "}
                <Code>Auto-detect</Code> for multilingual or code-switching
                conversations, or <Code>Lisan-ud-Dawat</Code> (LSD) for
                meetings spoken entirely in LSD — output will be in Arabic
                script.
              </p>
            </div>

            <div className="bg-surface rounded-lg border border-gray-800 px-4 py-3">
              <p className="text-sm font-semibold text-white mb-1">Model</p>
              <p className="text-sm text-gray-400">
                The Whisper model size. Larger models are more accurate but
                slower. See the{" "}
                <button
                  onClick={() => scrollTo("model-selection")}
                  className="text-primary underline underline-offset-2"
                >
                  Model Selection Guide
                </button>{" "}
                below for a full comparison.
              </p>
            </div>

            <div className="bg-surface rounded-lg border border-gray-800 px-4 py-3">
              <p className="text-sm font-semibold text-white mb-1">
                Diarize Speakers
              </p>
              <p className="text-sm text-gray-400">
                When enabled, each segment of the transcript is labeled with a
                speaker (e.g. SPEAKER_00, SPEAKER_01). Requires a valid{" "}
                <Code>HF_TOKEN</Code> environment variable. Adds processing
                time, especially on first run.
              </p>
            </div>

            <div className="bg-surface rounded-lg border border-gray-800 px-4 py-3">
              <p className="text-sm font-semibold text-white mb-1">Speakers</p>
              <p className="text-sm text-gray-400">
                The number of distinct speakers in the recording. Leave blank
                for automatic detection. Providing the correct count
                significantly improves diarization accuracy. Only active when
                Diarize Speakers is on.
              </p>
            </div>
          </div>

          {/* ── Speaker Diarization ─────────────────────────────────── */}
          <SectionHeading id="speaker-diarization">Speaker Diarization</SectionHeading>

          <Prose>
            Diarization is the process of partitioning an audio stream into
            segments according to who is speaking. When enabled, every line in
            the transcript is prefixed with a speaker label like{" "}
            <Code>SPEAKER_00</Code> or a resolved name if you have enrolled voice
            profiles.
          </Prose>

          <TipBox>
            If you know the exact number of speakers in a recording, enter it in
            the Speakers field. The diarization model performs noticeably better
            with a hint rather than having to guess.
          </TipBox>

          <SubHeading>Speaker Labels</SubHeading>
          <Prose>
            By default, speakers are labeled <Code>SPEAKER_00</Code>,{" "}
            <Code>SPEAKER_01</Code>, and so on. If you have enrolled voice
            profiles on the Speakers page, the system automatically tries to
            match each diarized speaker to a known profile. A successful match
            replaces the generic label with the person's name throughout the
            transcript.
          </Prose>

          <SubHeading>Automatic Matching</SubHeading>
          <Prose>
            When one or more voice profiles exist, the system compares speaker
            embeddings from the recording against all enrolled profiles. Matches
            above a confidence threshold are applied automatically. No manual
            re-labeling is needed.
          </Prose>

          {/* ── Speaker Enrollment ──────────────────────────────────── */}
          <SectionHeading id="speaker-enrollment">Speaker Enrollment (Voice Profiles)</SectionHeading>

          <Prose>
            Enrolling a voice profile lets AI MOM recognize that person in future
            meetings and replace the generic <Code>SPEAKER_XX</Code> label with
            their name automatically.
          </Prose>

          <SubHeading>How to Enroll</SubHeading>
          <ol className="space-y-2 mb-4">
            {[
              "Navigate to the Speakers page from the sidebar.",
              'Click "Enroll New Speaker" and enter the person\'s name.',
              "When prompted, speak naturally for 15–20 seconds. A quiet environment gives the best embedding.",
              "Submit the recording. The profile is saved and used in all future meetings.",
            ].map((step, i) => (
              <li key={i} className="flex gap-3 text-sm text-gray-300">
                <span className="bg-primary/20 text-primary text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>

          <TipBox>
            Re-enroll a speaker at any time to improve recognition accuracy —
            especially if they were initially enrolled in a noisy environment.
          </TipBox>

          <WarnBox>
            Voice profiles are stored locally. If the backend data directory is
            reset, all profiles must be re-enrolled.
          </WarnBox>

          {/* ── Language Support ────────────────────────────────────── */}
          <SectionHeading id="language-support">Language Support</SectionHeading>

          <div className="overflow-x-auto mb-4">
            <table className="w-full text-sm border border-gray-700 rounded-lg overflow-hidden">
              <thead>
                <tr className="bg-gray-800/60 text-left text-xs uppercase text-gray-400">
                  <th className="px-4 py-3 border-b border-gray-700">Language</th>
                  <th className="px-4 py-3 border-b border-gray-700">Code</th>
                  <th className="px-4 py-3 border-b border-gray-700">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                <tr>
                  <td className="px-4 py-3 text-white font-medium">English</td>
                  <td className="px-4 py-3"><Code>en</Code></td>
                  <td className="px-4 py-3 text-gray-400">Best accuracy; full structured minutes output</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-white font-medium">Auto-detect</td>
                  <td className="px-4 py-3"><Code>auto</Code> / <Code>multilingual</Code></td>
                  <td className="px-4 py-3 text-gray-400">Handles code-switching (e.g. LSD + English mixed). Whisper detects language per segment.</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-white font-medium">Lisan-ud-Dawat</td>
                  <td className="px-4 py-3"><Code>lsd</Code></td>
                  <td className="px-4 py-3 text-gray-400">Outputs transcript in Arabic script. Best for meetings conducted entirely in LSD.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <TipBox>
            For non-English or mixed-language audio, use the <Code>medium</Code>{" "}
            or <Code>large</Code> model. Smaller models are primarily optimized
            for English.
          </TipBox>

          {/* ── Model Selection ─────────────────────────────────────── */}
          <SectionHeading id="model-selection">Model Selection Guide</SectionHeading>

          <Prose>
            AI MOM uses OpenAI Whisper for transcription. Five model sizes are
            available. Choose based on how much time you can wait versus how
            accurate you need the transcript to be.
          </Prose>

          <div className="overflow-x-auto mb-4">
            <table className="w-full text-sm border border-gray-700 rounded-lg overflow-hidden">
              <thead>
                <tr className="bg-gray-800/60 text-left text-xs uppercase text-gray-400">
                  <th className="px-4 py-3 border-b border-gray-700">Model</th>
                  <th className="px-4 py-3 border-b border-gray-700">Speed</th>
                  <th className="px-4 py-3 border-b border-gray-700">Accuracy</th>
                  <th className="px-4 py-3 border-b border-gray-700">Best For</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {[
                  ["tiny", "Very Fast", "Low", "Quick drafts, testing"],
                  ["base", "Fast", "Moderate", "Short English meetings"],
                  ["small", "Balanced", "Good", "Most meetings (recommended)"],
                  ["medium", "Slow", "High", "Non-English, mixed language"],
                  ["large", "Very Slow", "Best", "Critical recordings"],
                ].map(([model, speed, accuracy, use]) => (
                  <tr key={model}>
                    <td className="px-4 py-3">
                      <Code>{model}</Code>
                      {model === "small" && (
                        <span className="ml-2 text-xs bg-primary/20 text-primary px-1.5 py-0.5 rounded-full">
                          default
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-300">{speed}</td>
                    <td className="px-4 py-3 text-gray-300">{accuracy}</td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{use}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <TipBox>
            <Code>small</Code> is the recommended starting point. Upgrade to{" "}
            <Code>medium</Code> or <Code>large</Code> only when you notice
            transcription errors or are processing non-English audio.
          </TipBox>

          {/* ── Understanding Minutes ───────────────────────────────── */}
          <SectionHeading id="understanding-minutes">Understanding Your Minutes</SectionHeading>

          <Prose>
            Once a job completes, the Minutes page presents the AI-generated
            output in several structured sections.
          </Prose>

          <div className="space-y-3 mb-4">
            {[
              {
                title: "Session Summary",
                desc: "A concise AI-generated overview of what was discussed during the meeting. Generated by the Gemini API.",
              },
              {
                title: "Key Decisions",
                desc: "A bullet list of decisions made or agreed upon during the meeting, extracted from the transcript.",
              },
              {
                title: "Action Items",
                desc: "A table listing tasks identified in the meeting, each with an owner (the person responsible) and a due date where mentioned.",
              },
              {
                title: "Next Steps",
                desc: "Follow-up items and open questions that were deferred for future discussion.",
              },
              {
                title: "Transcript",
                desc: "The full verbatim transcript. When diarization is enabled, each segment is prefixed with the speaker's name or label. Talk-time statistics are shown per speaker.",
              },
            ].map(({ title, desc }) => (
              <div
                key={title}
                className="bg-surface rounded-lg border border-gray-800 px-4 py-3"
              >
                <p className="text-sm font-semibold text-white mb-1">{title}</p>
                <p className="text-sm text-gray-400">{desc}</p>
              </div>
            ))}
          </div>

          <WarnBox>
            If the Session Summary, Key Decisions, or Action Items sections are
            empty, your <Code>GEMINI_API_KEY</Code> may not be configured. The
            transcript will still be available even without Gemini.
          </WarnBox>

          {/* ── Diarization Caching ─────────────────────────────────── */}
          <SectionHeading id="diarization-caching">Diarization Caching</SectionHeading>

          <Prose>
            Speaker diarization is computationally expensive. The first time you
            diarize a recording, expect it to take 5–20 minutes depending on the
            audio length and your hardware. Subsequent runs with the same audio
            file are served from cache and return almost instantly.
          </Prose>

          <SubHeading>How the Cache Works</SubHeading>
          <BulletList
            items={[
              "The cache key is derived from the audio file content and the num_speakers setting.",
              "Changing the num_speakers value for the same audio file will bypass the cache and trigger a fresh diarization run.",
              "The cache persists on disk across server restarts.",
              "Changing only the title, language, or model does not affect the diarization cache.",
            ]}
          />

          <TipBox>
            If you want to experiment with different speaker counts on the same
            recording, be aware that each distinct count requires a separate
            (slow) diarization run on the first attempt. After that, subsequent
            runs with the same count are fast.
          </TipBox>

          {/* ── Tips & Tricks ───────────────────────────────────────── */}
          <SectionHeading id="tips-tricks">Tips & Tricks</SectionHeading>

          <BulletList
            items={[
              "Record in a quiet environment — background noise is the biggest enemy of transcription accuracy.",
              "Enroll speakers before the meeting so auto-identification runs without any manual steps.",
              "If you know the number of speakers, always set the Speakers field — it is the single most impactful setting for diarization quality.",
              "For long meetings (30+ minutes), use the medium model to maintain accuracy throughout.",
              "Split very long recordings (2+ hours) into segments for faster, more reliable processing.",
              "When reviewing minutes, check the transcript first if any section looks wrong — the AI summary is only as good as the transcript beneath it.",
              "If a speaker is mis-identified, re-enroll them with a cleaner recording and re-process the job.",
            ]}
          />

          {/* ── API Keys ────────────────────────────────────────────── */}
          <SectionHeading id="api-keys">API Keys & Configuration</SectionHeading>

          <Prose>
            AI MOM relies on two external APIs. Both are configured via a{" "}
            <Code>.env</Code> file in the project root (next to{" "}
            <Code>docker-compose.yml</Code> or the backend entry point).
          </Prose>

          <CodeBlock>{`# .env
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSy_xxxxxxxxxxxxxxxxxxxxxxxxxxxx`}</CodeBlock>

          <div className="space-y-4 mb-4">
            <div className="bg-surface rounded-lg border border-gray-800 px-4 py-3">
              <p className="text-sm font-semibold text-white mb-1">
                HF_TOKEN — Hugging Face Token
              </p>
              <p className="text-sm text-gray-400 mb-2">
                Required for speaker diarization. The diarization pipeline
                (pyannote.audio) is gated on Hugging Face and requires an
                accepted-license token.
              </p>
              <p className="text-sm text-gray-400">
                Get one at{" "}
                <a
                  href="https://huggingface.co/settings/tokens"
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary underline underline-offset-2"
                >
                  huggingface.co/settings/tokens
                </a>
                . Make sure you have accepted the license for{" "}
                <Code>pyannote/speaker-diarization-3.1</Code> on the model
                page.
              </p>
            </div>

            <div className="bg-surface rounded-lg border border-gray-800 px-4 py-3">
              <p className="text-sm font-semibold text-white mb-1">
                GEMINI_API_KEY — Google Gemini Key
              </p>
              <p className="text-sm text-gray-400 mb-2">
                Required for AI summarization (session summary, key decisions,
                action items, next steps). Without this key the transcript is
                still generated but the structured minutes sections will be
                empty.
              </p>
              <p className="text-sm text-gray-400">
                Get one at{" "}
                <a
                  href="https://aistudio.google.com/app/apikey"
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary underline underline-offset-2"
                >
                  aistudio.google.com/app/apikey
                </a>
                .
              </p>
            </div>
          </div>

          <WarnBox>
            Never commit your <Code>.env</Code> file to version control. Add it
            to <Code>.gitignore</Code> if it is not already there.
          </WarnBox>

          <div className="mt-12 mb-4 border-t border-gray-800 pt-6">
            <p className="text-xs text-gray-600 text-center">
              AI MOM Documentation · Last updated March 2026
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
