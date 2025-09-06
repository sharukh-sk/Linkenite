import React, { useEffect, useState } from 'react';

function App() {
  const [emails, setEmails] = useState([]);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [responseText, setResponseText] = useState('');

  useEffect(() => {
    fetch('http://localhost:8000/emails')
      .then(res => res.json())
      .then(data => setEmails(data));
  }, []);

  const selectEmail = (email) => {
    setSelectedEmail(email);
    setResponseText(email.ai_response);
  };

  const saveResponse = () => {
    fetch(`http://localhost:8000/emails/${selectedEmail.id}/response`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ai_response: responseText }),
    }).then(() => alert('Response saved'));
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <div style={{ width: '40%', borderRight: '1px solid gray', padding: 10, overflowY: 'scroll' }}>
        <h2>Support Emails</h2>
        {emails.map(email => (
          <div
            key={email.id}
            onClick={() => selectEmail(email)}
            style={{
              cursor: 'pointer',
              marginBottom: 10,
              border: selectedEmail?.id === email.id ? '2px solid blue' : '1px solid #ccc',
              padding: 5,
              borderRadius: 4,
              backgroundColor: email.priority === 'Urgent' ? '#ffe6e6' : 'white'
            }}
          >
            <b>{email.subject}</b> <br />
            <small>From: {email.sender} | Priority: {email.priority} | Sentiment: {email.sentiment}</small>
          </div>
        ))}
      </div>
      <div style={{ width: '60%', padding: 10, overflowY: 'scroll' }}>
        {selectedEmail ? (
          <>
            <h3>{selectedEmail.subject}</h3>
            <p><b>From:</b> {selectedEmail.sender}</p>
            <p><b>Received:</b> {selectedEmail.sent_date}</p>
            <p><b>Body:</b> {selectedEmail.body}</p>
            <p><b>Phone Numbers:</b> {selectedEmail.phone_numbers.join(', ') || 'None'}</p>
            <p><b>Alternate Emails:</b> {selectedEmail.alternate_emails.join(', ') || 'None'}</p>
            <p><b>Customer Requests:</b> {selectedEmail.customer_requests.join(', ') || 'None'}</p>
            <p><b>Sentiment:</b> {selectedEmail.sentiment}</p>
            <p><b>Priority:</b> {selectedEmail.priority}</p>
            <h4>AI Draft Response</h4>
            <textarea
              rows={15}
              style={{ width: '100%' }}
              value={responseText}
              onChange={e => setResponseText(e.target.value)}
            />
            <button onClick={saveResponse} style={{ marginTop: 10, padding: '10px 20px' }}>Save Response</button>
          </>
        ) : (
          <p>Select an email to view details and response</p>
        )}
      </div>
    </div>
  );
}

export default App;