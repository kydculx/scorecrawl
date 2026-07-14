// LocalStorage keys
const STORAGE_KEYS = {
  SB_URL: 'scorecrawl_sb_url',
  SB_KEY: 'scorecrawl_sb_key',
  GH_PAT: 'scorecrawl_gh_pat',
  GH_REPO: 'scorecrawl_gh_repo',
  GH_WORKFLOW: 'scorecrawl_gh_workflow'
};

// League to Supabase Table Mapping
const LEAGUE_TABLES = {
  "K리그 1": "k_league_1",
  "K리그 2": "k_league_2",
  "프리미어리그": "premier_league",
  "분데스리가": "bundesliga",
  "라리가": "laliga",
  "J1리그": "j1_league",
  "세리에 A": "serie_a"
};

// Global State
let supabaseClient = null;
let fetchedData = [];
let statusInterval = null;

// DOM Elements
const selectLeague = document.getElementById('select-league');
const selectSeason = document.getElementById('select-season');
const btnFetch = document.getElementById('btn-fetch');
const btnExcel = document.getElementById('btn-excel');
const btnTrigger = document.getElementById('btn-trigger');
const inputMaxRounds = document.getElementById('input-max-rounds');

// Settings DOM
const btnSettings = document.getElementById('btn-settings');
const modalSettings = document.getElementById('settings-modal');
const btnCloseSettings = document.getElementById('btn-close-settings');
const btnSaveSettings = document.getElementById('btn-save-settings');

const setSbUrl = document.getElementById('setting-sb-url');
const setSbKey = document.getElementById('setting-sb-key');
const setGhPat = document.getElementById('setting-gh-pat');
const setGhRepo = document.getElementById('setting-gh-repo');
const setGhWorkflow = document.getElementById('setting-gh-workflow');

// Table DOM
const tableLoading = document.getElementById('table-loading');
const tableEmpty = document.getElementById('table-empty');
const tableWrapper = document.getElementById('table-wrapper');
const tableBody = document.getElementById('table-body');

// Action Status DOM
const statusBadge = document.getElementById('status-badge');
const statusTime = document.getElementById('status-time');
const statusLogLink = document.getElementById('status-log-link');

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide Icons
  lucide.createIcons();
  
  // Load Settings
  loadSettings();
  
  // Setup Supabase Client if configured
  initSupabase();
  
  // Setup Event Listeners
  btnFetch.addEventListener('click', fetchData);
  btnExcel.addEventListener('click', exportToExcel);
  btnTrigger.addEventListener('click', triggerWorkflow);
  
  btnSettings.addEventListener('click', () => modalSettings.classList.remove('hidden'));
  btnCloseSettings.addEventListener('click', () => modalSettings.classList.add('hidden'));
  btnSaveSettings.addEventListener('click', saveSettings);
  
  // Start polling GitHub workflow status
  startStatusPolling();
});

// Load Settings from LocalStorage
function loadSettings() {
  setSbUrl.value = localStorage.getItem(STORAGE_KEYS.SB_URL) || '';
  setSbKey.value = localStorage.getItem(STORAGE_KEYS.SB_KEY) || '';
  setGhPat.value = localStorage.getItem(STORAGE_KEYS.GH_PAT) || '';
  setGhRepo.value = localStorage.getItem(STORAGE_KEYS.GH_REPO) || '';
  setGhWorkflow.value = localStorage.getItem(STORAGE_KEYS.GH_WORKFLOW) || 'crawl.yml';
}

// Save Settings to LocalStorage
function saveSettings() {
  localStorage.setItem(STORAGE_KEYS.SB_URL, setSbUrl.value.trim());
  localStorage.setItem(STORAGE_KEYS.SB_KEY, setSbKey.value.trim());
  localStorage.setItem(STORAGE_KEYS.GH_PAT, setGhPat.value.trim());
  localStorage.setItem(STORAGE_KEYS.GH_REPO, setGhRepo.value.trim());
  localStorage.setItem(STORAGE_KEYS.GH_WORKFLOW, setGhWorkflow.value.trim());
  
  modalSettings.classList.add('hidden');
  initSupabase();
  alert('설정이 저장되었습니다.');
  
  // Restart status polling with new credentials
  startStatusPolling();
}

// Initialize Supabase Client
function initSupabase() {
  const url = localStorage.getItem(STORAGE_KEYS.SB_URL);
  const key = localStorage.getItem(STORAGE_KEYS.SB_KEY);
  
  if (url && key) {
    try {
      supabaseClient = supabase.createClient(url, key);
    } catch (e) {
      console.error('Supabase initialization failed:', e);
      supabaseClient = null;
    }
  } else {
    supabaseClient = null;
  }
}

// Fetch Data from Supabase
async function fetchData() {
  if (!supabaseClient) {
    alert('Supabase 연동 설정을 완료한 후 조회해 주세요.');
    modalSettings.classList.remove('hidden');
    return;
  }

  const league = selectLeague.value;
  const season = selectSeason.value;
  const tableName = LEAGUE_TABLES[league];

  if (!tableName) {
    alert('해당 리그에 대한 매핑 테이블을 찾을 수 없습니다.');
    return;
  }

  // UI States
  tableLoading.classList.remove('hidden');
  tableEmpty.classList.add('hidden');
  tableWrapper.classList.add('hidden');
  btnExcel.disabled = true;
  tableBody.innerHTML = '';
  fetchedData = [];

  try {
    const { data, error } = await supabaseClient
      .from(tableName)
      .select('*')
      .eq('시즌', season)
      .order('라운드', { ascending: true })
      .order('날짜', { ascending: true })
      .order('시간', { ascending: true });

    if (error) throw error;

    if (!data || data.length === 0) {
      tableEmpty.classList.remove('hidden');
      return;
    }

    fetchedData = data;
    renderTable(data);
    
    tableWrapper.classList.remove('hidden');
    btnExcel.disabled = false;
  } catch (err) {
    console.error('Error fetching data:', err);
    alert('데이터 조회 중 오류가 발생했습니다: ' + err.message);
    tableEmpty.classList.remove('hidden');
  } finally {
    tableLoading.classList.add('hidden');
  }
}

// Render Data to Table HTML
function renderTable(data) {
  tableBody.innerHTML = '';
  
  data.forEach(row => {
    const tr = document.createElement('tr');
    
    // Create elements matching headers
    const cells = [
      row.라운드 || '-',
      row.날짜 || '-',
      row.시간 || '-',
      row.홈 || '-',
      row.홈순위 ? `[${row.홈순위}]` : '-',
      `${row.홈점수 !== null && row.홈점수 !== undefined ? row.홈점수 : ''} - ${row.원정점수 !== null && row.원정점수 !== undefined ? row.원정점수 : ''}`,
      row.원정순위 ? `[${row.원정순위}]` : '-',
      row.원정 || '-',
      row.승 || '-',
      row.무 || '-',
      row.패 || '-',
      row.오버 || '-',
      row.오버라인 || '-',
      row.언더 || '-',
      row.핸디캡홈 || '-',
      row.핸디캡라인 || '-',
      row.핸디캡원정 || '-'
    ];

    cells.forEach((cellText, idx) => {
      const td = document.createElement('td');
      td.textContent = cellText;
      
      // Style classes
      if (idx === 3 || idx === 7) {
        td.classList.add('team-name');
      } else if (idx === 5) {
        td.classList.add('score');
      } else if (idx >= 8) {
        td.classList.add('odds');
      }
      
      tr.appendChild(td);
    });

    tableBody.appendChild(tr);
  });
}

// Export to Excel using SheetJS
function exportToExcel() {
  if (fetchedData.length === 0) return;

  const league = selectLeague.value;
  const season = selectSeason.value;

  // Format data specifically for export structure
  const exportRows = fetchedData.map(row => ({
    "리그": league,
    "시즌": season,
    "라운드": row.라운드,
    "날짜": row.날짜,
    "시간": row.시간,
    "홈": row.홈,
    "홈순위": row.홈순위,
    "홈점수": row.홈점수,
    "원정점수": row.원정점수,
    "원정순위": row.원정순위,
    "원정": row.원정,
    "승": row.승,
    "무": row.무,
    "패": row.패,
    "오버": row.오버,
    "오버라인": row.오버라인,
    "언더": row.언더,
    "핸디캡홈": row.핸디캡홈,
    "핸디캡라인": row.핸디캡라인,
    "핸디캡원정": row.핸디캡원정
  }));

  const worksheet = XLSX.utils.json_to_sheet(exportRows);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Matches");

  // Save File
  const filename = `${league}_${season}.xlsx`;
  XLSX.writeFile(workbook, filename);
}

// Trigger GitHub Actions Workflow
async function triggerWorkflow() {
  const pat = localStorage.getItem(STORAGE_KEYS.GH_PAT);
  const repo = localStorage.getItem(STORAGE_KEYS.GH_REPO);
  const workflow = localStorage.getItem(STORAGE_KEYS.GH_WORKFLOW) || 'crawl.yml';

  if (!pat || !repo) {
    alert('GitHub PAT 및 Repository 설정을 완료한 후 실행해 주세요.');
    modalSettings.classList.remove('hidden');
    return;
  }

  const league = selectLeague.value;
  const season = selectSeason.value;
  const maxRounds = inputMaxRounds.value.trim();

  if (!confirm(`${league} (${season}) 크롤링 작업을 실행하시겠습니까?`)) {
    return;
  }

  btnTrigger.disabled = true;
  updateStatusUI('queued', '크롤러 시작 요청 중...');

  try {
    const url = `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${pat}`,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      },
      body: JSON.stringify({
        ref: 'main',
        inputs: {
          league_name: league,
          season_name: season,
          max_rounds: maxRounds
        }
      })
    });

    if (response.status === 204) {
      alert('GitHub Actions가 성공적으로 트리거되었습니다. 약 10~20초 후 상태가 반영됩니다.');
      // Force status update shortly
      setTimeout(checkWorkflowStatus, 5000);
    } else {
      const errText = await response.text();
      throw new Error(`GitHub API HTTP ${response.status}: ${errText}`);
    }
  } catch (err) {
    console.error('Trigger workflow failed:', err);
    alert('Actions 트리거 오류: ' + err.message);
    btnTrigger.disabled = false;
    checkWorkflowStatus(); // Reset to current status
  }
}

// Start Status Polling
function startStatusPolling() {
  if (statusInterval) clearInterval(statusInterval);
  
  // Poll every 10 seconds
  checkWorkflowStatus();
  statusInterval = setInterval(checkWorkflowStatus, 10000);
}

// Check GitHub Actions Workflow Runs Status
async function checkWorkflowStatus() {
  const pat = localStorage.getItem(STORAGE_KEYS.GH_PAT);
  const repo = localStorage.getItem(STORAGE_KEYS.GH_REPO);
  const workflow = localStorage.getItem(STORAGE_KEYS.GH_WORKFLOW) || 'crawl.yml';

  if (!pat || !repo) {
    updateStatusUI('idle', '설정 필요');
    return;
  }

  try {
    const url = `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/runs?per_page=1`;
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${pat}`,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const resData = await response.json();
    const runs = resData.workflow_runs;

    if (!runs || runs.length === 0) {
      updateStatusUI('idle', '기존 실행 이력 없음');
      btnTrigger.disabled = false;
      return;
    }

    const latestRun = runs[0];
    const status = latestRun.status; // queued, in_progress, completed
    const conclusion = latestRun.conclusion; // success, failure, cancelled, etc.
    const runTime = new Date(latestRun.updated_at).toLocaleString();
    const logUrl = latestRun.html_url;

    let uiState = 'idle';
    let label = '대기';

    if (status === 'queued') {
      uiState = 'queued';
      label = '대기열 등록';
      btnTrigger.disabled = true;
    } else if (status === 'in_progress') {
      uiState = 'progress';
      label = '크롤링 진행 중';
      btnTrigger.disabled = true;
    } else if (status === 'completed') {
      btnTrigger.disabled = false;
      if (conclusion === 'success') {
        uiState = 'success';
        label = '수집 성공';
      } else {
        uiState = 'failure';
        label = `실패 (${conclusion})`;
      }
    }

    updateStatusUI(uiState, `${label} (${runTime})`, logUrl);
  } catch (err) {
    console.error('Check status error:', err);
    updateStatusUI('idle', '상태 확인 불가');
    btnTrigger.disabled = false;
  }
}

// Update Status Card UI
function updateStatusUI(state, text, logUrl = null) {
  // state: idle, queued, progress, success, failure
  statusBadge.className = `badge badge-${state}`;
  statusBadge.textContent = state === 'progress' ? 'RUNNING' : state.toUpperCase();
  statusTime.textContent = text;

  if (logUrl) {
    statusLogLink.href = logUrl;
    statusLogLink.classList.remove('hidden');
  } else {
    statusLogLink.classList.add('hidden');
  }
}
