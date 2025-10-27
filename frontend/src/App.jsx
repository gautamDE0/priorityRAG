import { useState, useEffect } from "react";
import axios from "axios";

function App() {
  const [user, setUser] = useState(null);
  const [emails, setEmails] = useState([]);
  const [priorities, setPriorities] = useState("");
  const [isPrioritizing, setIsPrioritizing] = useState(false);
  const [summary, setSummary] = useState(null);

  // Check for user data in URL on component mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const userData = params.get("user");
    if (userData) {
      try {
        const parsedUser = JSON.parse(decodeURIComponent(userData));
        setUser(parsedUser);
        // Clean up URL
        window.history.replaceState({}, document.title, "/");
      } catch (error) {
        console.error("Error parsing user data:", error);
      }
    }
  }, []);

  const handleLogin = async () => {
    try {
      const response = await axios.get("http://localhost:8000/login");
      // Redirect to Google's authorization URL
      window.location.href = response.data.authorization_url;
    } catch (error) {
      console.error("Login error:", error);
      alert("Failed to initiate login");
    }
  };

  const handleLogout = () => {
    setUser(null);
  };

  const fetchEmails = async () => {
    if (!user) {
      alert("Please login first");
      return;
    }
    
    try {
      const res = await axios.post("http://localhost:8000/api/fetch-emails", {
        user_id: user.sub
      });
      
      if (res.data.success) {
        setEmails(res.data.emails || []);
        if (res.data.emails.length === 0) {
          alert("No unread emails found");
        }
      }
    } catch (error) {
      console.error("Error fetching emails:", error);
      alert("Failed to fetch emails. Please try logging in again.");
    }
  };

  const prioritizeEmails = async () => {
    if (emails.length === 0) {
      alert("Please fetch emails first");
      return;
    }
    
    setIsPrioritizing(true);
    try {
      const res = await axios.post("http://localhost:8000/api/prioritize-emails", {
        emails: emails
      });
      
      if (res.data.success) {
        setEmails(res.data.emails);
        setSummary(res.data.summary);
        setPriorities(""); // Clear old text-based priorities
      }
    } catch (error) {
      console.error("Error prioritizing emails:", error);
      alert("Failed to prioritize emails");
    } finally {
      setIsPrioritizing(false);
    }
  };

  return (
    <div style={{ padding: 40, fontFamily: "Arial" }}>
      <h1>📧 Gmail RAG Prioritizer</h1>
      
      {user ? (
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {user.picture && <img src={user.picture} alt="Profile" style={{ width: 40, height: 40, borderRadius: "50%" }} />}
            <div>
              <strong>{user.name}</strong>
              <div style={{ fontSize: 12, color: "#666" }}>{user.email}</div>
            </div>
            <button onClick={handleLogout} style={{ marginLeft: 20 }}>Logout</button>
          </div>
        </div>
      ) : (
        <button onClick={handleLogin}>Sign in with Google</button>
      )}
      
      <button onClick={fetchEmails}>Fetch Emails</button>
      <button onClick={prioritizeEmails} disabled={isPrioritizing}>
        {isPrioritizing ? "Analyzing..." : "Prioritize with AI"}
      </button>
      
      {summary && (
        <div style={{ marginTop: 20, padding: 15, backgroundColor: "#f0f0f0", borderRadius: 5 }}>
          <h3>Priority Summary:</h3>
          <div style={{ display: "flex", gap: 20 }}>
            <span style={{ color: "red", fontWeight: "bold" }}>🔴 Urgent: {summary.red}</span>
            <span style={{ color: "orange", fontWeight: "bold" }}>🟡 Less Urgent: {summary.yellow}</span>
            <span style={{ color: "green", fontWeight: "bold" }}>🟢 Non-Urgent: {summary.green}</span>
          </div>
        </div>
      )}

      <div>
        <h3>Emails ({emails.length}):</h3>
        {emails.length === 0 ? (
          <p>No emails to display. Click "Fetch Emails" to load unread messages.</p>
        ) : (
          emails.map((email, i) => {
            // Determine urgency styling
            const urgencyColors = {
              red: { bg: "#ffebee", border: "#f44336", label: "🔴 URGENT" },
              yellow: { bg: "#fff9e6", border: "#ff9800", label: "🟡 LESS URGENT" },
              green: { bg: "#e8f5e9", border: "#4caf50", label: "🟢 NON-URGENT" }
            };
            
            const urgency = email.urgency_color || null;
            const style = urgency ? urgencyColors[urgency] : { bg: "#f9f9f9", border: "#ddd" };
            
            return (
              <div key={i} style={{ 
                marginBottom: 15, 
                padding: 15, 
                border: `2px solid ${style.border}`, 
                borderRadius: 5,
                backgroundColor: style.bg
              }}>
                {urgency && (
                  <div style={{ 
                    fontWeight: "bold", 
                    color: style.border, 
                    fontSize: 12, 
                    marginBottom: 8 
                  }}>
                    {style.label}
                  </div>
                )}
                <div style={{ fontWeight: "bold", fontSize: 16, marginBottom: 8, color: "#333" }}>
                  📧 {email.subject}
                </div>
                <div style={{ fontSize: 12, color: "#666", marginBottom: 3 }}>From: {email.from}</div>
                <div style={{ fontSize: 12, color: "#666", marginBottom: 10 }}>Date: {email.date}</div>
                
                {email.summary ? (
                  <div style={{ 
                    marginTop: 10,
                    padding: 10,
                    backgroundColor: "rgba(255, 255, 255, 0.7)",
                    borderLeft: "3px solid " + style.border,
                    borderRadius: 3
                  }}>
                    <div style={{ fontSize: 11, fontWeight: "bold", color: "#555", marginBottom: 5 }}>📝 AI SUMMARY:</div>
                    <div style={{ fontSize: 14, lineHeight: 1.5, color: "#333" }}>{email.summary}</div>
                  </div>
                ) : (
                  <div style={{ fontSize: 14, marginTop: 8, color: "#555" }}>{email.snippet}</div>
                )}
              </div>
            );
          })
        )}
      </div>

      <div>
        <h3>Prioritized Output:</h3>
        {priorities && <pre>{priorities}</pre>}
      </div>
    </div>
  );
}

export default App;
