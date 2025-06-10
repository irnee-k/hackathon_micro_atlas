chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "clipContent") {
        const url = request.url;
        const text = request.text;

        // !! IMPORTANT: Replace this with your current Ngrok HTTPS URL !!
        // You will need to update this every time your Ngrok URL changes.
        const flaskBackendUrl = "https://ebea-2601-189-8501-b450-75a7-ecfa-40ad-5d6c.ngrok-free.app/web_clip"; 

        fetch(flaskBackendUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ url: url, text: text })
        })
        .then(response => response.json())
        .then(data => {
            console.log("Clipper backend response:", data);
            sendResponse({ success: true, message: data.message });
        })
        .catch(error => {
            console.error("Clipper backend error:", error);
            sendResponse({ success: false, error: error.message });
        });

        return true; // Indicates we will send a response asynchronously
    }
});