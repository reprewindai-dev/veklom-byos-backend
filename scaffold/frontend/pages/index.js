import React, { useState, useEffect } from 'react';

export default function Dashboard() {
  const [formData, setFormData] = useState({ name: 'AlphaCorp', country: 'CA', age: 25, identity_score: 0.95 });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch('http://localhost:8088/api/v1/onboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          country: formData.country,
          age: parseInt(formData.age),
          identity_score: parseFloat(formData.identity_score)
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || data);
      } else {
        setResult(data);
      }
    } catch (e) {
      setError({ reason: 'Failed to connect to backend api. Is uvicorn running?' });
    }
    setLoading(false);
  };

  return (
    <div style={{
      backgroundColor: '#0a0a14',
      color: '#f3f4f6',
      minHeight: '100vh',
      fontFamily: 'system-ui, sans-serif',
      padding: '2rem 5%'
    }}>
      <header style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid #1e1e2f',
        paddingBottom: '1rem',
        marginBottom: '2rem'
      }}>
        <h1 style={{ margin: 0, fontSize: '1.8rem', color: '#a855f7' }}>VEKLOM CONTROL NODE</h1>
        <span style={{
          backgroundColor: '#10b981',
          color: '#022c22',
          padding: '4px 12px',
          borderRadius: '12px',
          fontWeight: 'bold',
          fontSize: '0.8rem'
        }}>SVID ACTIVE</span>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Run Controls */}
        <div style={{ backgroundColor: '#111122', padding: '1.5rem', borderRadius: '8px', border: '1px solid #1e1e2f' }}>
          <h2 style={{ color: '#06b6d4', marginBottom: '1.5rem', fontSize: '1.2rem' }}>Durable Execution Launcher</h2>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#9ca3af', marginBottom: '4px' }}>Representative Name</label>
            <input type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})}
              style={{ width: '100%', padding: '8px', background: '#0a0a14', border: '1px solid #2e2e4f', color: '#fff', borderRadius: '4px' }} />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#9ca3af', marginBottom: '4px' }}>ISO Country Code</label>
            <input type="text" value={formData.country} onChange={e => setFormData({...formData, country: e.target.value})}
              style={{ width: '100%', padding: '8px', background: '#0a0a14', border: '1px solid #2e2e4f', color: '#fff', borderRadius: '4px' }} />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#9ca3af', marginBottom: '4px' }}>Age</label>
            <input type="number" value={formData.age} onChange={e => setFormData({...formData, age: e.target.value})}
              style={{ width: '100%', padding: '8px', background: '#0a0a14', border: '1px solid #2e2e4f', color: '#fff', borderRadius: '4px' }} />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#9ca3af', marginBottom: '4px' }}>Biometric Score (0.00 - 1.00)</label>
            <input type="number" step="0.01" value={formData.identity_score} onChange={e => setFormData({...formData, identity_score: e.target.value})}
              style={{ width: '100%', padding: '8px', background: '#0a0a14', border: '1px solid #2e2e4f', color: '#fff', borderRadius: '4px' }} />
          </div>

          <button onClick={handleRun} disabled={loading} style={{
            width: '100%',
            padding: '12px',
            backgroundColor: '#a855f7',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            fontWeight: 'bold',
            cursor: 'pointer',
            transition: 'background-color 0.2s'
          }}>
            {loading ? 'Running Proof Solvers...' : 'Run Durable Agent Onboarding'}
          </button>
        </div>

        {/* Introspection Telemetry Panel */}
        <div style={{ backgroundColor: '#111122', padding: '1.5rem', borderRadius: '8px', border: '1px solid #1e1e2f', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h2 style={{ color: '#06b6d4', margin: 0, fontSize: '1.2rem' }}>Introspection & Evidence Telemetry</h2>

          {error && (
            <div style={{ backgroundColor: '#4c0519', border: '1px solid #f43f5e', padding: '1rem', borderRadius: '4px' }}>
              <h3 style={{ color: '#f43f5e', fontSize: '0.9rem', margin: '0 0 4px' }}>ePCA DEADLOCK TRIGGERED (UNSAT)</h3>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#fda4af' }}>{error.reason || JSON.stringify(error)}</p>
            </div>
          )}

          {result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ borderLeft: '4px solid #10b981', paddingLeft: '12px' }}>
                <h3 style={{ color: '#10b981', margin: '0 0 4px', fontSize: '0.9rem' }}>EXECUTION COMPLIANT (SAT)</h3>
                <p style={{ margin: 0, fontSize: '0.8rem', color: '#a7f3d0' }}>{result.proof_message}</p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div style={{ background: '#0a0a14', padding: '8px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>Semantic Drift Delta</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#f59e0b' }}>{result.drift_score}</div>
                </div>
                <div style={{ background: '#0a0a14', padding: '8px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>Token Budget Usage</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#06b6d4' }}>{result.token_budget_consumed} TOKENS</div>
                </div>
              </div>

              <div style={{ background: '#0a0a14', padding: '12px', borderRadius: '4px', border: '1px solid #1e1e2f' }}>
                <span style={{ fontSize: '0.7rem', color: '#9ca3af', display: 'block', marginBottom: '4px' }}>Audit Receipt ID (SVID-Signed)</span>
                <code style={{ fontSize: '0.8rem', color: '#a855f7', wordBreak: 'break-all' }}>{result.evidence_hash}</code>
              </div>
            </div>
          )}

          {!result && !error && (
            <div style={{ display: 'flex', flex: '1', justifyContent: 'center', alignItems: 'center', color: '#4b5563', fontSize: '0.9rem', border: '2px dashed #1e1e2f', borderRadius: '6px' }}>
              Pending execution trigger. Run the onboarding agent on the left.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
