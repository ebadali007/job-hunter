// Global Job Hunter AI Automation - Client Application Logic

let currentJobs = [];
let eventSource = null;
let searchDebounceTimer = null;
let isTerminalOpen = true;
let isAutoPilotActive = true;
let secondsRemaining = 3600;
let countdownTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    fetchStats();
    fetchJobs();
    fetchRecruiterReplies();
    initLiveStream();
    loadProfileSettings();

    // Auto-refresh stats every 15 seconds
    setInterval(fetchStats, 15000);

    // Countdown clock every second
    clearInterval(countdownTimer);
    countdownTimer = setInterval(tickCountdown, 1000);
});

// --- REAL-TIME SERVER-SENT EVENTS (SSE) STREAM ---
function initLiveStream() {
    if (eventSource) {
        eventSource.close();
    }
    eventSource = new EventSource('/api/hunt/stream');

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            appendTerminalLog(data.message);
        } catch (e) {
            appendTerminalLog(event.data);
        }
    };

    eventSource.onerror = () => {
        setTimeout(initLiveStream, 5000);
    };
}

function appendTerminalLog(msg) {
    const drawer = document.getElementById('terminal-drawer');
    const line = document.createElement('div');
    line.className = 'font-mono text-[11px] leading-relaxed py-0.5 border-b border-slate-900/40';

    if (msg.includes('HIGH MATCH') || msg.includes('✅') || msg.includes('🎉') || msg.includes('Auto-Apply Success')) {
        line.innerHTML = `<span class="text-emerald-400 font-semibold">${escapeHtml(msg)}</span>`;
    } else if (msg.includes('⚡') || msg.includes('🔎') || msg.includes('🚀') || msg.includes('Auto-Apply')) {
        line.innerHTML = `<span class="text-brand-400">${escapeHtml(msg)}</span>`;
    } else if (msg.includes('⚠️') || msg.includes('Safe Pause') || msg.includes('notice')) {
        line.innerHTML = `<span class="text-amber-400">${escapeHtml(msg)}</span>`;
    } else if (msg.includes('❌')) {
        line.innerHTML = `<span class="text-rose-400">${escapeHtml(msg)}</span>`;
    } else {
        line.innerHTML = `<span class="text-slate-300">${escapeHtml(msg)}</span>`;
    }

    drawer.appendChild(line);
    drawer.scrollTop = drawer.scrollHeight;

    if (msg.includes('Finished') || msg.includes('HIGH MATCH') || msg.includes('Auto-Apply Success')) {
        fetchStats();
        fetchJobs();
    }
}

function toggleTerminal() {
    const drawer = document.getElementById('terminal-drawer');
    const chevron = document.getElementById('terminal-chevron');
    isTerminalOpen = !isTerminalOpen;
    if (isTerminalOpen) {
        drawer.classList.remove('hidden');
        chevron.style.transform = 'rotate(0deg)';
    } else {
        drawer.classList.add('hidden');
        chevron.style.transform = 'rotate(-90deg)';
    }
}

// --- STATS & AUTOPILOT FETCHING ---
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        document.getElementById('stat-total').innerText = data.total_jobs || 0;
        document.getElementById('stat-high').innerText = data.high_matches || 0;
        document.getElementById('stat-tailored').innerText = data.tailored_count || 0;
        document.getElementById('stat-applied').innerText = data.applied_count || 0;
        document.getElementById('stat-replies').innerText = data.total_replies || 0;

        const unreadDot = document.getElementById('unread-dot');
        const replyBadge = document.getElementById('tab-reply-badge');

        if (data.unread_replies > 0) {
            unreadDot.classList.remove('hidden');
            replyBadge.classList.remove('hidden');
            replyBadge.innerText = data.unread_replies;
        } else {
            unreadDot.classList.add('hidden');
            replyBadge.classList.add('hidden');
        }

        // Auto-pilot status update
        isAutoPilotActive = Boolean(data.auto_pilot_enabled);
        secondsRemaining = data.seconds_until_next_hunt || 3600;
        updateAutoPilotDisplay();

        // Update hunt button animation
        const huntBtn = document.getElementById('btn-start-hunt');
        const huntText = document.getElementById('hunt-text');
        const terminalStatus = document.getElementById('terminal-status');

        if (data.is_hunting) {
            huntText.innerText = "Searching & Applying...";
            huntBtn.classList.add('ring-2', 'ring-brand-400', 'pulse-glow');
            terminalStatus.innerText = "(Autonomous Job Hunt Running...)";
            terminalStatus.className = "text-emerald-400 font-mono text-[11px] animate-pulse";
        } else {
            huntText.innerText = "Run Hunt Now";
            huntBtn.classList.remove('ring-2', 'ring-brand-400', 'pulse-glow');
            terminalStatus.innerText = isAutoPilotActive ? "(Auto-Pilot Active • Ready)" : "(Auto-Pilot Paused)";
            terminalStatus.className = isAutoPilotActive ? "text-emerald-400 font-mono text-[11px]" : "text-slate-500 font-mono text-[11px]";
        }
    } catch (e) {
        console.error("Failed to load stats", e);
    }
}

function updateAutoPilotDisplay() {
    const statusBadge = document.getElementById('autopilot-status-badge');
    const toggleBtn = document.getElementById('btn-toggle-autopilot');
    const toggleText = document.getElementById('autopilot-toggle-text');
    const pulseDot = document.getElementById('autopilot-pulse-dot');

    if (isAutoPilotActive) {
        statusBadge.innerText = "ACTIVE (Autonomous Search & Auto-Apply)";
        statusBadge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40";
        toggleText.innerText = "Pause Auto-Pilot";
        pulseDot.className = "w-3.5 h-3.5 rounded-full bg-emerald-400 pulse-glow";
    } else {
        statusBadge.innerText = "PAUSED (Manual Mode)";
        statusBadge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-700 text-slate-300 border border-slate-600";
        toggleText.innerText = "Resume Auto-Pilot";
        pulseDot.className = "w-3.5 h-3.5 rounded-full bg-slate-600";
    }
}

function tickCountdown() {
    if (isAutoPilotActive && secondsRemaining > 0) {
        secondsRemaining--;
    }
    const mins = Math.floor(secondsRemaining / 60);
    const secs = secondsRemaining % 60;
    const countdownEl = document.getElementById('autopilot-countdown');
    if (countdownEl) {
        if (isAutoPilotActive) {
            countdownEl.innerText = `Next Auto-Scan & Apply in: ${mins}m ${secs < 10 ? '0' : ''}${secs}s`;
        } else {
            countdownEl.innerText = `Auto-Pilot is Paused`;
        }
    }
}

async function toggleAutoPilotState() {
    const newState = !isAutoPilotActive;
    try {
        const res = await fetch('/api/autopilot/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: newState })
        });
        const data = await res.json();
        isAutoPilotActive = data.auto_pilot_enabled;
        updateAutoPilotDisplay();
        appendTerminalLog(`ℹ️ [Auto-Pilot] Toggled to: ${isAutoPilotActive ? 'ACTIVE' : 'PAUSED'}`);
    } catch (e) {
        alert("Failed to toggle auto-pilot: " + e.message);
    }
}

// --- TRIGGER IMMEDIATE JOB HUNT ---
async function triggerJobHunt() {
    const huntBtn = document.getElementById('btn-start-hunt');
    huntBtn.disabled = true;
    try {
        const res = await fetch('/api/hunt', { method: 'POST' });
        const data = await res.json();
        appendTerminalLog(`🚀 ${data.message}`);
        fetchStats();
    } catch (e) {
        appendTerminalLog(`❌ Failed to trigger job hunt: ${e}`);
    } finally {
        setTimeout(() => { huntBtn.disabled = false; }, 2000);
    }
}

// --- FETCH & RENDER JOBS ---
function debounceFetchJobs() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(fetchJobs, 350);
}

function updateScoreLabel(val) {
    document.getElementById('score-label').innerText = val + '%';
}

async function fetchJobs() {
    const container = document.getElementById('jobs-container');
    const minScore = document.getElementById('filter-min-score').value || 0;
    const status = document.getElementById('filter-status').value || 'all';
    const search = document.getElementById('filter-search').value.trim();

    try {
        let url = `/api/jobs?min_score=${minScore}&status=${status}&limit=60`;
        if (search) {
            url += `&search=${encodeURIComponent(search)}`;
        }

        const res = await fetch(url);
        currentJobs = await res.json();

        if (!currentJobs || currentJobs.length === 0) {
            container.innerHTML = `
                <div class="glass-card rounded-2xl p-12 text-center text-slate-400">
                    <i data-lucide="inbox" class="w-12 h-12 mx-auto text-slate-600 mb-3"></i>
                    <h3 class="text-base font-semibold text-slate-200">No Fresh (&lt;24h) Jobs Found For Current Criteria</h3>
                    <p class="text-xs text-slate-400 max-w-md mx-auto mt-1 mb-4">Click "Run Hunt Now" above to query worldwide live job boards or adjust the Match Score filter.</p>
                    <button onclick="triggerJobHunt()" class="px-4 py-2 bg-brand-500 text-white rounded-xl text-xs font-semibold hover:bg-brand-600">Run Fresh Hunt Now</button>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        container.innerHTML = currentJobs.map(job => renderJobCard(job)).join('');
        lucide.createIcons();
    } catch (e) {
        console.error("Error fetching jobs", e);
        container.innerHTML = `<div class="p-6 text-rose-400 text-xs">Error loading jobs: ${e.message}</div>`;
    }
}

function renderJobCard(job) {
    const score = job.match_score || 0;
    let badgeColor = "bg-slate-700 text-slate-300 border-slate-600";
    if (score >= 85) {
        badgeColor = "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm shadow-emerald-500/10";
    } else if (score >= 75) {
        badgeColor = "bg-brand-500/20 text-brand-300 border-brand-500/40";
    } else if (score >= 60) {
        badgeColor = "bg-amber-500/20 text-amber-300 border-amber-500/40";
    }

    const reasons = Array.isArray(job.match_reasons) ? job.match_reasons : [];
    const gaps = Array.isArray(job.skill_gaps) ? job.skill_gaps : [];
    const isTailored = Boolean(job.tailored_cv_path);
    const isApplied = job.status === 'applied';

    return `
    <div class="glass-card rounded-2xl p-5 border border-slate-800 hover:border-slate-700 transition-all duration-200 space-y-4">
        <!-- Top Row: Title, Company, Score -->
        <div class="flex items-start justify-between gap-4">
            <div class="space-y-1 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                    <h3 class="text-base font-bold text-slate-100 hover:text-brand-400 transition-colors">${escapeHtml(job.title)}</h3>
                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider bg-slate-800 text-slate-400 border border-slate-700">${escapeHtml(job.source)}</span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">⚡ &lt;24H FRESH</span>
                    ${isApplied ? '<span class="px-2.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center space-x-1"><span>✅ AUTO-APPLIED</span></span>' : ''}
                </div>
                <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
                    <span class="font-semibold text-brand-400">${escapeHtml(job.company)}</span>
                    <span>•</span>
                    <span class="flex items-center space-x-1">
                        <i data-lucide="map-pin" class="w-3.5 h-3.5 text-slate-500"></i>
                        <span>${escapeHtml(job.location || 'Worldwide Remote')}</span>
                    </span>
                    <span>•</span>
                    <span class="text-indigo-300 flex items-center space-x-1">
                        <i data-lucide="dollar-sign" class="w-3.5 h-3.5 text-indigo-400"></i>
                        <span>${escapeHtml(job.salary || 'Competitive')}</span>
                    </span>
                </div>
            </div>

            <!-- Match Score Pill -->
            <div class="flex flex-col items-end">
                <div class="px-3.5 py-1.5 rounded-full border text-xs font-bold font-mono flex items-center space-x-1.5 ${badgeColor}">
                    <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
                    <span>${score}% Match</span>
                </div>
            </div>
        </div>

        <!-- AI Match Bullets & Skill Gaps -->
        <div class="bg-slate-900/70 border border-slate-800/80 rounded-xl p-3.5 space-y-2 text-xs">
            <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                <i data-lucide="bot" class="w-3.5 h-3.5 text-brand-400"></i>
                <span>AI Skill Match Highlights:</span>
            </div>
            <ul class="space-y-1 text-slate-300 pl-4 list-disc marker:text-brand-400">
                ${reasons.map(r => `<li>${escapeHtml(r)}</li>`).join('') || '<li>High correlation in modern engineering and development practices.</li>'}
            </ul>
            ${gaps.length > 0 ? `
            <div class="pt-2 border-t border-slate-800 text-[11px] text-slate-400">
                <span class="font-semibold text-amber-400/90">Gap Analysis:</span> ${escapeHtml(gaps.join(' • '))}
            </div>` : ''}
        </div>

        <!-- Action Buttons Row -->
        <div class="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/70">
            <!-- Left: Tailored Documents Downloads -->
            <div class="flex flex-wrap items-center gap-2">
                ${isTailored ? `
                <a href="/api/jobs/${job.id}/download/cv" target="_blank" class="px-3 py-1.5 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30 text-xs font-medium flex items-center space-x-1.5 transition-colors">
                    <i data-lucide="file-text" class="w-3.5 h-3.5 text-indigo-400"></i>
                    <span>Tailored CV (PDF)</span>
                </a>
                <a href="/api/jobs/${job.id}/download/cover_letter" target="_blank" class="px-3 py-1.5 rounded-lg bg-emerald-600/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-600/30 text-xs font-medium flex items-center space-x-1.5 transition-colors">
                    <i data-lucide="mail" class="w-3.5 h-3.5 text-emerald-400"></i>
                    <span>Cover Letter (PDF)</span>
                </a>
                <button onclick="openPreviewModal(${job.id})" class="px-2.5 py-1.5 text-xs text-slate-400 hover:text-slate-200 border border-slate-800 hover:bg-slate-800 rounded-lg transition-colors">
                    Preview
                </button>
                ` : `
                <span class="text-[11px] text-slate-500 italic">Score below auto-tailor threshold</span>
                `}
            </div>

            <!-- Right: Playwright Auto-Apply & Direct Link -->
            <div class="flex items-center space-x-2">
                <button onclick="runPlaywrightAssistant(${job.id})" title="Launch safe Playwright assistant to auto-apply" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium flex items-center space-x-1.5 transition-colors">
                    <i data-lucide="wand-2" class="w-3.5 h-3.5 text-brand-400"></i>
                    <span>Auto-Apply (Playwright)</span>
                </button>

                <a href="${escapeHtml(job.apply_url)}" target="_blank" rel="noopener noreferrer" class="px-4 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-sm transition-colors">
                    <span>Direct Link</span>
                    <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                </a>

                <button onclick="toggleAppliedStatus(${job.id}, '${isApplied ? 'matched' : 'applied'}')" title="${isApplied ? 'Unmark Applied' : 'Mark Applied'}" class="p-1.5 rounded-lg border ${isApplied ? 'bg-amber-500/20 text-amber-400 border-amber-500/40' : 'text-slate-500 hover:text-slate-200 border-slate-800'} transition-colors">
                    <i data-lucide="check-circle-2" class="w-4 h-4"></i>
                </button>
            </div>
        </div>
    </div>
    `;
}

// --- TOGGLE APPLIED STATUS ---
async function toggleAppliedStatus(jobId, newStatus) {
    try {
        await fetch(`/api/jobs/${jobId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        fetchStats();
        fetchJobs();
    } catch (e) {
        alert("Failed to update status: " + e.message);
    }
}

// --- PLAYWRIGHT SAFE AUTO-FILL ---
async function runPlaywrightAssistant(jobId) {
    appendTerminalLog(`🤖 Launching Playwright Auto-Apply Assistant for Job #${jobId}...`);
    try {
        const res = await fetch('/api/playwright/autofill', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: jobId })
        });
        const report = await res.json();

        if (report.captcha_detected) {
            alert(`⚠️ Anti-Bot Protection Alert:\n${report.message}\n\nAutomated submission paused safely to protect your profile.`);
            appendTerminalLog(`⚠️ [Playwright Alert] ${report.message}`);
        } else if (report.status === 'prefilled_ready') {
            alert(`✅ Safe Pre-Fill Completed!\n\nFilled Fields: ${report.fields_filled.join(', ')}\n\nFinal review left for candidate submission.`);
            appendTerminalLog(`✅ [Playwright Success] Pre-filled ${report.fields_filled.length} form inputs.`);
        } else {
            alert(`Playwright Assistant: ${report.message}`);
            appendTerminalLog(`ℹ️ [Playwright] ${report.message}`);
        }
        fetchStats();
        fetchJobs();
    } catch (e) {
        alert("Error launching Playwright: " + e.message);
    }
}

// --- DOCUMENT PREVIEW MODAL ---
function openPreviewModal(jobId) {
    const job = currentJobs.find(j => j.id === jobId);
    if (!job) return;

    document.getElementById('modal-title').innerText = `${job.title} @ ${job.company}`;
    document.getElementById('modal-subtitle').innerText = `${job.match_score}% Match Score • ${job.location}`;
    document.getElementById('modal-resume-summary').innerText = job.tailored_resume_summary || "ATS Resume Summary ready.";
    document.getElementById('modal-cover-letter').innerText = job.tailored_cover_letter_text || "Custom Cover Letter ready.";

    const actionsContainer = document.getElementById('modal-download-actions');
    actionsContainer.innerHTML = `
        <a href="/api/jobs/${job.id}/download/cv" target="_blank" class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold">Download CV (PDF)</a>
        <a href="/api/jobs/${job.id}/download/cover_letter" target="_blank" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold">Download Cover Letter (PDF)</a>
    `;

    document.getElementById('preview-modal').classList.remove('hidden');
}

function closePreviewModal() {
    document.getElementById('preview-modal').classList.add('hidden');
}

// --- RECRUITER INBOX TAB ---
async function fetchRecruiterReplies() {
    const container = document.getElementById('recruiter-replies-container');
    try {
        const res = await fetch('/api/recruiter-replies');
        const replies = await res.json();

        if (!replies || replies.length === 0) {
            container.innerHTML = `
                <div class="glass-card rounded-2xl p-12 text-center text-slate-400">
                    <i data-lucide="mail-open" class="w-10 h-10 mx-auto text-slate-600 mb-2"></i>
                    <h3 class="text-sm font-semibold text-slate-200">No Recruiter Responses Yet</h3>
                    <p class="text-xs text-slate-400 max-w-sm mx-auto mt-1">Once you apply and companies reply, our 24/7 IMAP engine automatically detects invitations and highlights them here.</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        container.innerHTML = replies.map(r => `
            <div class="glass-card rounded-2xl p-4 border border-slate-800 space-y-2">
                <div class="flex items-start justify-between">
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-bold text-slate-100 text-xs">${escapeHtml(r.sender_name || r.sender_email)}</span>
                            <span class="text-[10px] px-2 py-0.5 rounded font-bold uppercase ${getSentimentBadge(r.sentiment)}">${escapeHtml(r.sentiment)}</span>
                        </div>
                        <h4 class="text-xs font-semibold text-brand-300 mt-0.5">${escapeHtml(r.subject)}</h4>
                    </div>
                    <span class="text-[10px] text-slate-500">${escapeHtml(r.received_at || '')}</span>
                </div>
                <p class="text-xs text-slate-300 bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 leading-relaxed">${escapeHtml(r.body_snippet)}</p>
                <div class="flex justify-end">
                    ${!r.is_read ? `
                    <button onclick="markReplyAsRead(${r.id})" class="text-[11px] text-brand-400 hover:underline">Mark as Read</button>
                    ` : '<span class="text-[11px] text-slate-600">Read</span>'}
                </div>
            </div>
        `).join('');
        lucide.createIcons();
    } catch (e) {
        console.error("Error fetching recruiter replies", e);
    }
}

function getSentimentBadge(sentiment) {
    switch (sentiment) {
        case 'interview_invite': return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
        case 'assessment': return 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40';
        case 'offer': return 'bg-amber-500/20 text-amber-300 border border-amber-500/40';
        default: return 'bg-slate-800 text-slate-300 border border-slate-700';
    }
}

async function checkInboxNow() {
    appendTerminalLog("📬 Scanning Gmail inbox via IMAP for recruiter replies...");
    try {
        const res = await fetch('/api/email/check', { method: 'POST' });
        const data = await res.json();
        appendTerminalLog(`✅ IMAP check finished. Found ${data.count} items.`);
        fetchRecruiterReplies();
        fetchStats();
    } catch (e) {
        appendTerminalLog(`❌ IMAP check error: ${e}`);
    }
}

async function markReplyAsRead(replyId) {
    try {
        await fetch(`/api/recruiter-replies/${replyId}/read`, { method: 'POST' });
        fetchRecruiterReplies();
        fetchStats();
    } catch (e) {
        console.error(e);
    }
}

// --- TABS SWITCHING ---
function switchTab(tabName) {
    const jobsTabContent = document.getElementById('jobs-tab-content');
    const recruiterTabContent = document.getElementById('recruiter-tab-content');
    const tabBtnJobs = document.getElementById('tab-btn-jobs');
    const tabBtnRecruiter = document.getElementById('tab-btn-recruiter');

    if (tabName === 'jobs-tab') {
        jobsTabContent.classList.remove('hidden');
        recruiterTabContent.classList.add('hidden');
        tabBtnJobs.className = "px-4 py-2 rounded-xl text-xs font-semibold bg-brand-500/10 text-brand-400 border border-brand-500/30 flex items-center space-x-2 transition-all";
        tabBtnRecruiter.className = "px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 flex items-center space-x-2 transition-all";
    } else {
        jobsTabContent.classList.add('hidden');
        recruiterTabContent.classList.remove('hidden');
        tabBtnRecruiter.className = "px-4 py-2 rounded-xl text-xs font-semibold bg-brand-500/10 text-brand-400 border border-brand-500/30 flex items-center space-x-2 transition-all";
        tabBtnJobs.className = "px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 flex items-center space-x-2 transition-all";
        fetchRecruiterReplies();
    }
}

// --- SETTINGS MODAL ---
async function loadProfileSettings() {
    try {
        const res = await fetch('/api/profile');
        const data = await res.json();
        if (data.profile && data.profile.name) {
            document.getElementById('candidate-name-badge').innerText = data.profile.name;
        }
        document.getElementById('settings-target-roles').value = (data.target_roles || []).join(', ');
        document.getElementById('settings-target-locations').value = (data.target_locations || []).join(', ');
        document.getElementById('settings-threshold').value = data.match_threshold || 75;

        // Auto-pilot & 24h limits
        const maxAgeInput = document.getElementById('settings-max-age');
        if (maxAgeInput) maxAgeInput.value = 24;

        const autoApplyCheckbox = document.getElementById('settings-auto-apply');
        if (autoApplyCheckbox) autoApplyCheckbox.checked = true;
    } catch (e) {
        console.error("Error loading settings", e);
    }
}

function openSettingsModal() {
    loadProfileSettings();
    document.getElementById('settings-modal').classList.remove('hidden');
}

function closeSettingsModal() {
    document.getElementById('settings-modal').classList.add('hidden');
}

async function saveSettings() {
    const rolesStr = document.getElementById('settings-target-roles').value;
    const locsStr = document.getElementById('settings-target-locations').value;
    const threshold = parseInt(document.getElementById('settings-threshold').value, 10);
    const geminiKey = document.getElementById('settings-gemini-key').value.trim();
    const gmailUser = document.getElementById('settings-gmail-user').value.trim();
    const gmailPwd = document.getElementById('settings-gmail-app-pwd').value.trim();

    const maxAge = parseInt(document.getElementById('settings-max-age').value, 10) || 24;
    const autoApply = document.getElementById('settings-auto-apply').checked;

    const payload = {
        target_roles: rolesStr.split(',').map(s => s.trim()).filter(Boolean),
        target_locations: locsStr.split(',').map(s => s.trim()).filter(Boolean),
        match_threshold: threshold,
        max_job_age_hours: maxAge,
        auto_apply_enabled: autoApply
    };
    if (geminiKey) payload.gemini_api_key = geminiKey;
    if (gmailUser) payload.gmail_user = gmailUser;
    if (gmailPwd) payload.gmail_app_password = gmailPwd;

    try {
        const res = await fetch('/api/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const resp = await res.json();
        alert(resp.message || "Settings saved!");
        closeSettingsModal();
        fetchStats();
        fetchJobs();
    } catch (e) {
        alert("Error saving settings: " + e.message);
    }
}

// --- UTILITIES ---
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
