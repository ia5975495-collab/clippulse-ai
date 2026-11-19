// AI Viral Video Clipper - Frontend Logic

document.addEventListener("DOMContentLoaded", () => {
    // State variables
    let currentVideoFilename = null;
    let currentJobId = null;
    let pollInterval = null;
    let hasServerApiKey = false;

    // DOM Elements
    const apiKeyBtn = document.getElementById("apiKeyBtn");
    const apiKeyModal = document.getElementById("apiKeyModal");
    const closeModalBtn = document.getElementById("closeModalBtn");
    const saveApiKeyBtn = document.getElementById("saveApiKeyBtn");
    const apiKeyInput = document.getElementById("apiKeyInput");
    const apiKeyDot = document.getElementById("apiKeyDot");
    const apiKeyStatusText = document.getElementById("apiKeyStatusText");
    const toggleApiKeyVisibility = document.getElementById("toggleApiKeyVisibility");

    const tabUpload = document.getElementById("tabUpload");
    const tabYoutube = document.getElementById("tabYoutube");
    const uploadContainer = document.getElementById("uploadContainer");
    const youtubeContainer = document.getElementById("youtubeContainer");
    const dropZone = document.getElementById("dropZone");
    const videoFileInput = document.getElementById("videoFileInput");
    const uploadProgressBar = document.getElementById("uploadProgressBar");
    const uploadBarFill = document.getElementById("uploadBarFill");
    const uploadPercent = document.getElementById("uploadPercent");
    const uploadStatusText = document.getElementById("uploadStatusText");

    const ytUrlInput = document.getElementById("ytUrlInput");
    const downloadYtBtn = document.getElementById("downloadYtBtn");

    const videoPreviewCard = document.getElementById("videoPreviewCard");
    const videoFilename = document.getElementById("videoFilename");
    const videoMeta = document.getElementById("videoMeta");
    const sourceVideoPlayer = document.getElementById("sourceVideoPlayer");
    const removeVideoBtn = document.getElementById("removeVideoBtn");

    const minDurSlider = document.getElementById("minDurSlider");
    const maxDurSlider = document.getElementById("maxDurSlider");
    const minDurText = document.getElementById("minDurText");
    const maxDurText = document.getElementById("maxDurText");
    const durationRangeLabel = document.getElementById("durationRangeLabel");

    const numClipBtns = document.querySelectorAll(".num-clip-btn");
    const numClipsInput = document.getElementById("numClipsInput");
    const numClipsLabel = document.getElementById("numClipsLabel");

    const cropOptions = document.querySelectorAll(".crop-option");
    const cropModeInput = document.getElementById("cropModeInput");

    const topicFocusInput = document.getElementById("topicFocusInput");
    const generateBtn = document.getElementById("generateBtn");

    const processingSection = document.getElementById("processingSection");
    const processingTitle = document.getElementById("processingTitle");
    const processingSub = document.getElementById("processingSub");
    const processingPercent = document.getElementById("processingPercent");
    const processingBarFill = document.getElementById("processingBarFill");

    const errorBanner = document.getElementById("errorBanner");
    const errorBannerMsg = document.getElementById("errorBannerMsg");
    const closeErrorBtn = document.getElementById("closeErrorBtn");

    if (closeErrorBtn) {
        closeErrorBtn.addEventListener("click", () => {
            errorBanner.classList.add("hidden");
        });
    }

    function showError(msg) {
        if (errorBanner && errorBannerMsg) {
            errorBannerMsg.textContent = msg;
            errorBanner.classList.remove("hidden");
            errorBanner.scrollIntoView({ behavior: 'smooth' });
        } else {
            alert(`Error: ${msg}`);
        }
    }

    const step1Indicator = document.getElementById("step1Indicator");
    const step2Indicator = document.getElementById("step2Indicator");
    const step3Indicator = document.getElementById("step3Indicator");
    const step4Indicator = document.getElementById("step4Indicator");

    const resultsSection = document.getElementById("resultsSection");
    const clipsCountBadge = document.getElementById("clipsCountBadge");
    const clipsGrid = document.getElementById("clipsGrid");

    // 1. Initial Config & API Key Handling
    fetch("/api/config")
        .then(res => res.json())
        .then(config => {
            hasServerApiKey = config.has_env_key;
            updateApiKeyUI();
        })
        .catch(() => updateApiKeyUI());

    function getApiKey() {
        if (hasServerApiKey) return "SERVER_ENV_KEY";
        return localStorage.getItem("GEMINI_API_KEY") || "";
    }

    function updateApiKeyUI() {
        const storedKey = localStorage.getItem("GEMINI_API_KEY");
        if (hasServerApiKey || (storedKey && storedKey.length > 5)) {
            apiKeyDot.className = "w-2 h-2 rounded-full bg-emerald-400";
            apiKeyStatusText.textContent = hasServerApiKey ? "Gemini Key: Active (Env)" : "Gemini Key: Configured";
            apiKeyBtn.classList.add("border-emerald-500/40");
        } else {
            apiKeyDot.className = "w-2 h-2 rounded-full bg-amber-400";
            apiKeyStatusText.textContent = "Set Gemini API Key";
            apiKeyBtn.classList.remove("border-emerald-500/40");
        }
    }

    apiKeyBtn.addEventListener("click", () => {
        apiKeyInput.value = localStorage.getItem("GEMINI_API_KEY") || "";
        apiKeyModal.classList.remove("hidden");
    });

    closeModalBtn.addEventListener("click", () => apiKeyModal.classList.add("hidden"));

    saveApiKeyBtn.addEventListener("click", () => {
        const key = apiKeyInput.value.trim();
        if (key) {
            localStorage.setItem("GEMINI_API_KEY", key);
            updateApiKeyUI();
            apiKeyModal.classList.add("hidden");
            checkGenerateReady();
        } else {
            alert("Please enter a valid Gemini API Key.");
        }
    });

    toggleApiKeyVisibility.addEventListener("click", () => {
        if (apiKeyInput.type === "password") {
            apiKeyInput.type = "text";
            toggleApiKeyVisibility.innerHTML = '<i class="fa-regular fa-eye-slash"></i>';
        } else {
            apiKeyInput.type = "password";
            toggleApiKeyVisibility.innerHTML = '<i class="fa-regular fa-eye"></i>';
        }
    });

    // 2. Tabs Switcher
    tabUpload.addEventListener("click", () => {
        tabUpload.className = "px-3 py-1 rounded-md font-medium bg-brand-600 text-white transition-all";
        tabYoutube.className = "px-3 py-1 rounded-md font-medium text-slate-400 hover:text-slate-200 transition-all";
        uploadContainer.classList.remove("hidden");
        youtubeContainer.classList.add("hidden");
    });

    tabYoutube.addEventListener("click", () => {
        tabYoutube.className = "px-3 py-1 rounded-md font-medium bg-red-600 text-white transition-all";
        tabUpload.className = "px-3 py-1 rounded-md font-medium text-slate-400 hover:text-slate-200 transition-all";
        youtubeContainer.classList.remove("hidden");
        uploadContainer.classList.add("hidden");
    });

    // 3. File Upload Drag & Drop
    dropZone.addEventListener("click", () => videoFileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add("drag-over");
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove("drag-over");
        }, false);
    });

    dropZone.addEventListener("drop", (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    videoFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    function handleFileUpload(file) {
        if (!file.type.startsWith("video/") && !file.name.match(/\.(mp4|mkv|mov|webm)$/i)) {
            alert("Please select a valid video file (MP4, MKV, MOV, WEBM).");
            return;
        }

        const formData = new FormData();
        formData.append("video", file);

        uploadProgressBar.classList.remove("hidden");
        uploadStatusText.textContent = `Uploading ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)...`;
        uploadPercent.textContent = "0%";
        uploadBarFill.style.width = "0%";

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/upload", true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                uploadPercent.textContent = `${percent}%`;
                uploadBarFill.style.width = `${percent}%`;
            }
        };

        xhr.onload = () => {
            uploadProgressBar.classList.add("hidden");
            if (xhr.status === 200) {
                const resp = JSON.parse(xhr.responseText);
                setLoadedVideo(resp);
            } else {
                let err = "Upload failed.";
                try { err = JSON.parse(xhr.responseText).error || err; } catch (e) {}
                alert(`Error: ${err}`);
            }
        };

        xhr.onerror = () => {
            uploadProgressBar.classList.add("hidden");
            alert("Network error during file upload.");
        };

        xhr.send(formData);
    }

    // 4. YouTube Link Fetch
    downloadYtBtn.addEventListener("click", () => {
        const url = ytUrlInput.value.trim();
        if (!url) {
            alert("Please enter a YouTube video URL.");
            return;
        }

        downloadYtBtn.disabled = true;
        downloadYtBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Fetching...';

        fetch("/api/youtube", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        })
        .then(res => res.json())
        .then(data => {
            downloadYtBtn.disabled = false;
            downloadYtBtn.innerHTML = '<span>Fetch</span> <i class="fa-solid fa-arrow-down"></i>';
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                setLoadedVideo(data);
            }
        })
        .catch(err => {
            downloadYtBtn.disabled = false;
            downloadYtBtn.innerHTML = '<span>Fetch</span> <i class="fa-solid fa-arrow-down"></i>';
            alert(`Network error: ${err.message}`);
        });
    });

    function setLoadedVideo(info) {
        currentVideoFilename = info.filename;
        videoFilename.textContent = info.filename;
        const durMin = Math.floor(info.duration / 60);
        const durSec = Math.floor(info.duration % 60);
        const timeStr = `${durMin}:${durSec < 10 ? '0' : ''}${durSec}`;
        videoMeta.textContent = `Duration: ~${timeStr} min | Resolution: ${info.width}x${info.height}`;

        sourceVideoPlayer.src = info.preview_url;
        videoPreviewCard.classList.remove("hidden");
        dropZone.classList.add("hidden");
        checkGenerateReady();
    }

    removeVideoBtn.addEventListener("click", () => {
        currentVideoFilename = null;
        sourceVideoPlayer.pause();
        sourceVideoPlayer.src = "";
        videoPreviewCard.classList.add("hidden");
        dropZone.classList.remove("hidden");
        videoFileInput.value = "";
        checkGenerateReady();
    });

    // 5. Duration Sliders Controls (10s to 120s / 2min)
    function updateDurationDisplay() {
        let minVal = parseInt(minDurSlider.value);
        let maxVal = parseInt(maxDurSlider.value);

        if (minVal > maxVal) {
            maxVal = minVal;
            maxDurSlider.value = maxVal;
        }

        minDurText.textContent = `${minVal}s`;
        maxDurText.textContent = `${maxVal}s`;
        durationRangeLabel.textContent = `${minVal}s - ${maxVal}s`;
    }

    minDurSlider.addEventListener("input", updateDurationDisplay);
    maxDurSlider.addEventListener("input", updateDurationDisplay);

    // 6. Number of Clips Buttons
    numClipBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            numClipBtns.forEach(b => {
                b.className = "num-clip-btn py-1.5 rounded-lg border border-dark-600 bg-dark-900/60 text-xs font-medium text-slate-300 hover:border-brand-500";
            });
            btn.className = "num-clip-btn active-chip py-1.5 rounded-lg border border-brand-500 bg-brand-600 text-xs font-bold text-white";
            const val = btn.getAttribute("data-val");
            numClipsInput.value = val;
            numClipsLabel.textContent = `${val} Clips`;
        });
    });

    // 7. Crop Mode Framing Selection (9:16)
    cropOptions.forEach(opt => {
        opt.addEventListener("click", () => {
            cropOptions.forEach(o => {
                o.className = "cursor-pointer border border-dark-700 bg-dark-900/60 rounded-xl p-2.5 text-center flex flex-col items-center space-y-1.5 transition-all crop-option";
                const icon = o.querySelector("i");
                if (icon) icon.className = icon.className.replace("text-brand-accent", "text-slate-400");
            });
            opt.className = "cursor-pointer border border-brand-500/80 bg-brand-500/10 rounded-xl p-2.5 text-center flex flex-col items-center space-y-1.5 transition-all crop-option";
            const activeIcon = opt.querySelector("i");
            if (activeIcon) activeIcon.className = activeIcon.className.replace("text-slate-400", "text-brand-accent");

            const mode = opt.getAttribute("data-crop");
            cropModeInput.value = mode;
        });
    });

    function checkGenerateReady() {
        const hasKey = hasServerApiKey || Boolean(localStorage.getItem("GEMINI_API_KEY"));
        const hasVideo = Boolean(currentVideoFilename);
        generateBtn.disabled = !(hasVideo);
    }

    // 8. Generate Viral Clips Trigger
    generateBtn.addEventListener("click", () => {
        if (!currentVideoFilename) {
            alert("Please upload a video first.");
            return;
        }

        const apiKey = localStorage.getItem("GEMINI_API_KEY") || "";
        if (!hasServerApiKey && !apiKey) {
            apiKeyModal.classList.remove("hidden");
            return;
        }

        const payload = {
            filename: currentVideoFilename,
            api_key: apiKey,
            min_duration: parseInt(minDurSlider.value),
            max_duration: parseInt(maxDurSlider.value),
            num_clips: parseInt(numClipsInput.value),
            crop_mode: cropModeInput.value,
            topic_focus: topicFocusInput.value.trim()
        };

        generateBtn.disabled = true;
        if (errorBanner) errorBanner.classList.add("hidden");
        resultsSection.classList.add("hidden");
        processingSection.classList.remove("hidden");
        resetProgressUI();

        fetch("/api/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
                generateBtn.disabled = false;
                processingSection.classList.add("hidden");
            } else {
                currentJobId = data.job_id;
                startPolling(currentJobId);
            }
        })
        .catch(err => {
            showError(`Failed to start processing: ${err.message}`);
            generateBtn.disabled = false;
            processingSection.classList.add("hidden");
        });
    });

    function resetProgressUI() {
        processingPercent.textContent = "10%";
        processingBarFill.style.width = "10%";
        processingTitle.textContent = "Starting Video Analysis...";
        processingSub.textContent = "Extracting audio stream for AI analysis";

        step1Indicator.className = "font-medium text-brand-accent";
        step2Indicator.className = "font-medium text-slate-400";
        step3Indicator.className = "font-medium text-slate-400";
        step4Indicator.className = "font-medium text-slate-400";
    }

    function startPolling(jobId) {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(() => {
            fetch(`/api/status/${jobId}`)
                .then(res => res.json())
                .then(job => {
                    if (job.error) {
                        clearInterval(pollInterval);
                        showError(`Processing Failed: ${job.error}`);
                        processingSection.classList.add("hidden");
                        generateBtn.disabled = false;
                        return;
                    }

                    const progress = job.progress || 10;
                    processingPercent.textContent = `${progress}%`;
                    processingBarFill.style.width = `${progress}%`;
                    processingTitle.textContent = job.message || "Processing video...";

                    // Update steps
                    if (job.status === "extracting_audio") {
                        step1Indicator.className = "font-medium text-brand-accent animate-pulse";
                    } else if (job.status === "uploading_ai") {
                        step1Indicator.className = "font-medium text-emerald-400";
                        step2Indicator.className = "font-medium text-brand-accent animate-pulse";
                    } else if (job.status === "analyzing") {
                        step1Indicator.className = "font-medium text-emerald-400";
                        step2Indicator.className = "font-medium text-emerald-400";
                        step3Indicator.className = "font-medium text-brand-accent animate-pulse";
                    } else if (job.status === "rendering") {
                        step1Indicator.className = "font-medium text-emerald-400";
                        step2Indicator.className = "font-medium text-emerald-400";
                        step3Indicator.className = "font-medium text-emerald-400";
                        step4Indicator.className = "font-medium text-brand-accent animate-pulse";
                    }

                    if (job.status === "completed") {
                        clearInterval(pollInterval);
                        step4Indicator.className = "font-medium text-emerald-400";
                        processingSection.classList.add("hidden");
                        generateBtn.disabled = false;
                        renderClips(job.clips || []);
                    }
                })
                .catch(err => {
                    console.error("Polling error:", err);
                });
        }, 1500);
    }

    function renderClips(clips) {
        clipsGrid.innerHTML = "";
        clipsCountBadge.textContent = `${clips.length} Clips`;

        if (clips.length === 0) {
            clipsGrid.innerHTML = `<p class="col-span-full text-center text-slate-400 py-8">No clips were generated.</p>`;
            resultsSection.classList.remove("hidden");
            return;
        }

        clips.forEach((clip, idx) => {
            const card = document.createElement("div");
            card.className = "clip-card bg-dark-800/90 border border-dark-700/80 rounded-2xl overflow-hidden shadow-xl flex flex-col";

            // Determine badge color
            const score = clip.virality_score || 85;
            let scoreBadgeClass = "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
            if (score >= 90) {
                scoreBadgeClass = "bg-rose-500/20 text-rose-300 border-rose-500/30 viral-pulse-badge";
            } else if (score < 75) {
                scoreBadgeClass = "bg-amber-500/20 text-amber-300 border-amber-500/30";
            }

            card.innerHTML = `
                <!-- Video Container (9:16 Vertical) -->
                <div class="relative w-full aspect-9-16 bg-black">
                    <video 
                        src="${clip.video_url}" 
                        poster="${clip.thumbnail_url}" 
                        controls 
                        playsinline 
                        preload="metadata" 
                        class="w-full h-full object-cover">
                    </video>
                    <!-- Floating Score Badge -->
                    <div class="absolute top-3 left-3 z-10">
                        <span class="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold border backdrop-blur-md ${scoreBadgeClass}">
                            <i class="fa-solid fa-fire text-[10px]"></i>
                            <span>${score}/100 Virality</span>
                        </span>
                    </div>
                    <!-- Duration Badge -->
                    <div class="absolute top-3 right-3 z-10">
                        <span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-black/60 backdrop-blur-md text-slate-200 border border-white/10">
                            ⏱️ ${clip.duration}s
                        </span>
                    </div>
                </div>

                <!-- Info Body -->
                <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
                    <div class="space-y-1.5">
                        <h4 class="font-bold text-sm text-slate-100 leading-snug line-clamp-2">${clip.title}</h4>
                        ${clip.hook ? `<p class="text-[11px] text-brand-accent line-clamp-2"><strong>Hook:</strong> "${clip.hook}"</p>` : ''}
                        ${clip.why_viral ? `<p class="text-[11px] text-slate-400 line-clamp-2">${clip.why_viral}</p>` : ''}
                    </div>

                    <!-- Actions -->
                    <div class="pt-2 border-t border-dark-700/60 flex items-center justify-between">
                        <span class="text-[10px] text-slate-500">
                            Start: ${Math.floor(clip.start_time / 60)}:${Math.floor(clip.start_time % 60).toString().padStart(2, '0')}
                        </span>
                        <a 
                            href="${clip.video_url}" 
                            download="${clip.filename}" 
                            class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md transition-all">
                            <i class="fa-solid fa-download"></i>
                            <span>Download 9:16</span>
                        </a>
                    </div>
                </div>
            `;

            clipsGrid.appendChild(card);
        });

        resultsSection.classList.remove("hidden");
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

});
