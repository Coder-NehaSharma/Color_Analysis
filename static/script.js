document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const videoFeed = document.getElementById('videoFeed');
    const videoPlaceholder = document.getElementById('videoPlaceholder');
    const videoOverlay = document.getElementById('videoOverlay');
    const toggleBtn = document.getElementById('toggleBtn');
    const lightingSelect = document.getElementById('lightingSelect');

    // Boxes
    const boxDisplays = [
        document.getElementById('box1Display'),
        document.getElementById('box2Display'),
        document.getElementById('box3Display'),
        document.getElementById('box4Display')
    ];
    const boxHexes = [
        document.getElementById('box1Hex'),
        document.getElementById('box2Hex'),
        document.getElementById('box3Hex'),
        document.getElementById('box4Hex')
    ];

    const maxDeltaEValue = document.getElementById('maxDeltaEValue');
    const passFailBadge = document.getElementById('passFailBadge');
    const statusMessage = document.getElementById('statusMessage');

    let isRunning = false;
    let pollInterval = null;

    // --- API Interactions ---

    function updateDashboard() {
        if (!isRunning) return;

        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                // Update Boxes
                data.box_colors.forEach((color, index) => {
                    if (boxDisplays[index]) {
                        boxDisplays[index].style.backgroundColor = color;
                        // Display Similarity Percentage (or "Reference")
                        if (data.similarities && data.similarities[index]) {
                            boxHexes[index].textContent = data.similarities[index];
                        } else {
                            boxHexes[index].textContent = color; // Fallback
                        }
                    }
                });

                // Update Results
                maxDeltaEValue.textContent = data.max_delta_e.toFixed(2);
                passFailBadge.textContent = data.pass_fail;
                statusMessage.textContent = data.status_message;

                // Style Pass/Fail Badge
                passFailBadge.className = 'status-badge'; // Reset
                if (data.pass_fail === 'PASS') {
                    passFailBadge.classList.add('pass');
                } else if (data.pass_fail === 'FAIL') {
                    passFailBadge.classList.add('fail');
                } else if (data.pass_fail === 'MIXED') {
                    passFailBadge.classList.add('mixed');
                    passFailBadge.style.backgroundColor = "rgba(250, 204, 21, 0.2)";
                    passFailBadge.style.color = "#facc15";
                    passFailBadge.style.border = "1px solid #facc15";
                }
            })
            .catch(error => console.error('Error fetching status:', error));
    }

    function setLighting(lighting) {
        fetch('/api/set_lighting', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lighting: lighting })
        });
    }

    function startAnalysis() {
        const url = document.getElementById('cameraUrl').value;

        fetch('/api/set_camera', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    isRunning = true;
                    videoFeed.src = "/video_feed?" + new Date().getTime();
                    videoFeed.style.display = "block";
                    videoOverlay.style.display = "block";
                    videoPlaceholder.style.display = "none";

                    toggleBtn.innerHTML = '<span class="icon">⏹</span> Stop Analysis';
                    toggleBtn.classList.add('stop');

                    pollInterval = setInterval(updateDashboard, 500);
                } else {
                    alert("Failed to set camera: " + data.message);
                }
            })
            .catch(error => {
                console.error('Error setting camera:', error);
                alert("Error connecting to server");
            });
    }

    function stopAnalysis() {
        isRunning = false;
        videoFeed.src = "";
        videoFeed.style.display = "none";
        videoOverlay.style.display = "none";
        videoPlaceholder.style.display = "flex";

        toggleBtn.innerHTML = '<span class="icon">▶</span> Start Analysis';
        toggleBtn.classList.remove('stop');

        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    // --- Event Listeners ---

    toggleBtn.addEventListener('click', () => {
        if (isRunning) {
            stopAnalysis();
        } else {
            startAnalysis();
        }
    });

    lightingSelect.addEventListener('change', (e) => {
        setLighting(e.target.value);
    });
});
