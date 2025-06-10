document.addEventListener('DOMContentLoaded', () => {
    const clipButton = document.getElementById('clipButton');
    const selectedTextDisplay = document.getElementById('selectedTextDisplay');
    const statusDiv = document.getElementById('status');

    // Request selected text from content.js when popup loads
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const activeTab = tabs[0];
        if (activeTab) {
            chrome.scripting.executeScript({
                target: { tabId: activeTab.id },
                function: getSelectionText,
            }, (results) => {
                if (results && results[0] && results[0].result) {
                    const selectedText = results[0].result;
                    selectedTextDisplay.textContent = selectedText.length > 0 ? selectedText : "No text selected.";
                    // Store it in session for clipping
                    chrome.storage.session.set({ clippedText: selectedText });
                }
            });
        }
    });

    // Function to be injected and get selected text
    function getSelectionText() {
        return window.getSelection().toString();
    }

    clipButton.addEventListener('click', () => {
        chrome.storage.session.get('clippedText', (data) => {
            const textToClip = data.clippedText || '';
            if (textToClip.length === 0 || textToClip === "No text selected.") {
                statusDiv.textContent = "Please select some text first!";
                statusDiv.style.color = 'red';
                return;
            }

            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                const activeTab = tabs[0];
                if (activeTab) {
                    const currentUrl = activeTab.url;
                    statusDiv.textContent = "Clipping...";
                    statusDiv.style.color = 'gray';

                    // Send message to background.js
                    chrome.runtime.sendMessage({
                        action: "clipContent",
                        url: currentUrl,
                        text: textToClip
                    }, (response) => {
                        if (response && response.success) {
                            statusDiv.textContent = "Clipped successfully!";
                            statusDiv.style.color = 'green';
                        } else {
                            statusDiv.textContent = "Clipping failed: " + (response ? response.error : "Unknown error");
                            statusDiv.style.color = 'red';
                        }
                    });
                }
            });
        });
    });
});