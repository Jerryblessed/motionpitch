const socket = io();
const logWindow = document.getElementById('logWindow');

socket.on('log', data => { 
    logWindow.style.display = 'block';
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerText = `[${new Date().toLocaleTimeString().split(' ')[0]}] ${data.msg}`;
    logWindow.appendChild(entry);
    logWindow.scrollTop = logWindow.scrollHeight;
});

function openModal(id) { 
    document.getElementById(id).style.display = 'flex'; 
}

function closeModal(id) { 
    document.getElementById(id).style.display = 'none'; 
}

async function generate() {
    const btn = document.querySelector('.btn-primary');
    const formData = new FormData();
    
    formData.append('topic', document.getElementById('topic').value);
    formData.append('slide_count', document.getElementById('slides').value);
    formData.append('enable_video', document.getElementById('enableVideo').checked);
    formData.append('url_link', document.getElementById('url_link').value);
    
    if(document.getElementById('pdf_file').files[0]) {
        formData.append('pdf_file', document.getElementById('pdf_file').files[0]);
    }

    if(!document.getElementById('topic').value) {
        return alert("Enter a topic");
    }
    
    btn.disabled = true; 
    btn.innerText = "Processing..."; 
    logWindow.innerHTML = ''; 
    logWindow.style.display = 'block';
    
    try {
        const res = await fetch('/generate', { 
            method: 'POST', 
            body: formData 
        });
        const data = await res.json();
        
        if(data.success) {
            window.location.href = data.redirect;
        } else { 
            alert(data.error); 
            btn.disabled = false; 
            btn.innerText = "✨ Generate"; 
        }
    } catch(e) { 
        console.error(e); 
        alert("An error occurred. Please try again.");
        btn.disabled = false; 
        btn.innerText = "✨ Generate"; 
    }
}
