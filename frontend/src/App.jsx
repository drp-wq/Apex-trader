import React, { useState, useEffect } from 'react';

export default function App() {
  const [safety, setSafety] = useState(null);
  const [account, setAccount] = useState({ balance: 514.75, equity: 514.75, unrealized_pnl: 0, open_positions_count: 0 });
  const [positions, setPositions] = useState({});
  const [statusMsg, setStatusMsg] = useState('');

  const fetchState = async () => {
    try {
      const sRes = await fetch('/safety');
      if (sRes.ok) setSafety(await sRes.json());

      const aRes = await fetch('/paper/account');
      if (aRes.ok) setAccount(await aRes.json());

      const pRes = await fetch('/paper/positions');
      if (pRes.ok) setPositions(await pRes.json());
    } catch (e) {
      console.warn("Backend connecting...");
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 1500);
    return () => clearInterval(interval);
  }, []);

  const handleFlatten = async () => {
    try {
      const prices = {};
      Object.keys(positions).forEach(s => prices[s] = positions[s].entry_price);
      const res = await fetch('/paper/flatten', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prices)
      });
      if (res.ok) {
        setStatusMsg('ALL POSITIONS FLATTENED (PAPER)');
        fetchState();
      }
    } catch (err) {
      setStatusMsg('Flatten Error: ' + err.message);
    }
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '16px' }}>
      {/* Header & Safety Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1f2937', paddingBottom: '12px' }}>
        <div>
          <h1 style={{ fontSize: '20px', margin: 0, color: '#60a5fa' }}>APEX TRADER</h1>
          <span style={{ fontSize: '11px', color: '#9ca3af' }}>Smart Money Concepts Research Engine</span>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ backgroundColor: '#065f46', color: '#34d399', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 'bold' }}>
            ● PAPER MODE ONLY
          </span>
          <div style={{ fontSize: '10px', color: '#ef4444', marginTop: '4px' }}>LIVE EXECUTION DISABLED</div>
        </div>
      </div>

      {/* Account Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px', marginTop: '16px' }}>
        <div style={{ background: '#111827', padding: '12px', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>PAPER BALANCE</div>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#f3f4f6' }}>${account.balance.toFixed(2)}</div>
        </div>
        <div style={{ background: '#111827', padding: '12px', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>EQUITY</div>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#f3f4f6' }}>${account.equity.toFixed(2)}</div>
        </div>
        <div style={{ background: '#111827', padding: '12px', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>UNREALIZED PNL</div>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: account.unrealized_pnl >= 0 ? '#10b981' : '#ef4444' }}>
            ${account.unrealized_pnl.toFixed(2)}
          </div>
        </div>
        <div style={{ background: '#111827', padding: '12px', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#9ca3af' }}>OPEN POSITIONS</div>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#f3f4f6' }}>{account.open_positions_count}</div>
        </div>
      </div>

      {/* Active Positions & Emergency Flatten */}
      <div style={{ background: '#111827', padding: '16px', borderRadius: '8px', marginTop: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '16px', margin: 0, color: '#f3f4f6' }}>Active Paper Positions</h2>
          {Object.keys(positions).length > 0 && (
            <button 
              onClick={handleFlatten}
              style={{ backgroundColor: '#dc2626', color: 'white', border: 'none', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 'bold', cursor: 'pointer' }}
            >
              EMERGENCY FLATTEN
            </button>
          )}
        </div>

        {Object.keys(positions).length === 0 ? (
          <div style={{ fontSize: '13px', color: '#6b7280', textAlign: 'center', padding: '20px 0' }}>No active positions</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {Object.values(positions).map(p => (
              <div key={p.symbol} style={{ display: 'flex', justifyContent: 'space-between', background: '#1f2937', padding: '10px 14px', borderRadius: '6px' }}>
                <div>
                  <span style={{ fontWeight: 'bold', color: '#f3f4f6' }}>{p.symbol}</span>
                  <span style={{ marginLeft: '8px', color: p.direction === 'BUY' ? '#34d399' : '#f87171', fontSize: '12px' }}>{p.direction}</span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '13px' }}>Entry: ${p.entry_price} | Qty: {p.quantity}</div>
                  <div style={{ fontSize: '12px', color: p.unrealized_pnl >= 0 ? '#34d399' : '#f87171' }}>
                    PnL: ${p.unrealized_pnl}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {statusMsg && (
        <div style={{ marginTop: '12px', background: '#374151', padding: '8px 12px', borderRadius: '6px', fontSize: '12px', color: '#93c5fd' }}>
          {statusMsg}
        </div>
      )}
    </div>
  );
}
