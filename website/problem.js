const API_URL = 'https://9l2ww5xs2b.execute-api.us-east-1.amazonaws.com/prod';

class ProblemPage {
    constructor(problemNumber) {
        this.problemNumber = problemNumber;
        this.autoRefresh = true;
        this.init();
    }

    init() {
        this.usernameInput = document.getElementById('username');
        this.submitBtn = document.getElementById('submitBtn');
        this.howToBtn = document.getElementById('howToBtn');
        this.toggleRefreshBtn = document.getElementById('toggleRefresh');
        this.refreshStatus = document.getElementById('refreshStatus');
        this.gameStatus = document.getElementById('gameStatus');
        this.modal = document.getElementById('howToModal');
        this.closeBtn = document.querySelector('.close');

        this.bindEvents();
        this.loadGameState();
        this.loadLeaderboard();
        setInterval(() => {
            if (this.autoRefresh) {
                this.loadGameState();
                this.loadLeaderboard();
            }
        }, 5000);
    }

    bindEvents() {
        this.usernameInput.addEventListener('input', () => {
            this.submitBtn.disabled = !this.usernameInput.value.trim();
        });

        this.submitBtn.addEventListener('click', () => this.handleSubmit());
        this.howToBtn.addEventListener('click', () => this.showHowTo());
        this.closeBtn.addEventListener('click', () => this.modal.style.display = 'none');
        this.toggleRefreshBtn.addEventListener('click', () => this.toggleRefresh());

        window.addEventListener('click', (e) => {
            if (e.target === this.modal) this.modal.style.display = 'none';
        });
    }

    async handleSubmit() {
        const username = this.usernameInput.value.trim();
        if (!username) return;

        const rule = await fetch('rule.md').then(r => r.text());
        const ruleWithUsername = rule
            .replace(/<USERNAME>/g, username)
            .replace(/<PROBLEM_NUMBER>/g, this.problemNumber);
        
        try {
            await navigator.clipboard.writeText(ruleWithUsername);
            alert('✅ ルールをクリップボードにコピーしました！\nLLMに貼り付けてコードを生成してください。');
        } catch (err) {
            const textarea = document.createElement('textarea');
            textarea.value = ruleWithUsername;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            alert('✅ ルールをクリップボードにコピーしました！\nLLMに貼り付けてコードを生成してください。');
        }
    }

    async showHowTo() {
        const rule = await fetch('rule.md').then(r => r.text());
        const preview = rule
            .replace(/<USERNAME>/g, 'example-user')
            .replace(/<PROBLEM_NUMBER>/g, this.problemNumber);
        document.getElementById('rulePreview').textContent = preview;
        this.modal.style.display = 'block';
    }

    toggleRefresh() {
        this.autoRefresh = !this.autoRefresh;
        this.refreshStatus.textContent = `自動更新: ${this.autoRefresh ? 'ON' : 'OFF'}`;
        this.toggleRefreshBtn.textContent = this.autoRefresh ? '⏸️ 停止' : '▶️ 再開';
    }

    async loadGameState() {
        try {
            const response = await fetch(`${API_URL}/game-state`);
            const data = await response.json();
            if (data.is_active) {
                this.gameStatus.textContent = '🟢 ゲーム進行中';
                this.gameStatus.style.color = '#007600';
            } else {
                this.gameStatus.textContent = '🔴 ゲーム停止中';
                this.gameStatus.style.color = '#d13212';
            }
        } catch (error) {
            console.error('Failed to load game state:', error);
        }
    }

    async loadLeaderboard() {
        try {
            const response = await fetch(`${API_URL}/leaderboard`);
            const data = await response.json();
            const tbody = document.getElementById('leaderboard');
            tbody.textContent = '';
            
            const items = Array.isArray(data) ? data : [];
            const problemData = items
                .filter(item => item.problem_number === this.problemNumber)
                .sort((a, b) => a.timestamp - b.timestamp);
            
            problemData.forEach((item, index) => {
                const row = document.createElement('tr');
                const rank = document.createElement('td');
                rank.className = 'rank';
                rank.textContent = `#${index + 1}`;
                const username = document.createElement('td');
                username.textContent = item.username;
                const timestamp = document.createElement('td');
                timestamp.textContent = new Date(item.timestamp).toLocaleString('ja-JP', {timeZone: 'Asia/Tokyo'});
                row.append(rank, username, timestamp);
                tbody.appendChild(row);
            });
        } catch (error) {
            console.error('Failed to load leaderboard:', error);
        }
    }
}
