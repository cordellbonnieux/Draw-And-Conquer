import React from 'react';

export type Player = {
  id: string;
  name: string;
  score: number;
};

export type ScoreBoardProps = {
  uuid: string,
  players: Player[];
  currentPlayerId: string;
};

export default function ScoreBoard({ uuid, players, currentPlayerId }: ScoreBoardProps) {
  // Sort players by score descending
  const sortedPlayers = [...players].sort((a, b) => b.score - a.score);

  // Compute ranks with handling for ties
  let lastScore: number | null = null;
  let lastRank = 0;
  let skip = 1;
  const ranks = sortedPlayers.map((player, idx) => {
    if (lastScore === null || player.score !== lastScore) {
      lastRank = idx + 1;
      skip = 1;
    } else {
      skip++;
    }
    lastScore = player.score;
    return lastRank;
  });

  return (
    <div style={{ display: 'flex', justifyContent: 'center', margin: '2rem 0' }}>
      <table
        style={{
          width: '400px',
          borderCollapse: 'collapse',
          background: '#fff',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        }}
      >
        <thead>
          <tr style={{ background: '#f5f5f5' }}>
            <th style={{ border: '1px solid #ddd', padding: '10px 0' }}>Rank</th>
            <th style={{ border: '1px solid #ddd', padding: '10px 0' }}>Name</th>
            <th style={{ border: '1px solid #ddd', padding: '10px 0' }}>Score</th>
          </tr>
        </thead>
        <tbody>
          {sortedPlayers.map((player, idx) => (
            <tr
              key={player.id}
              style={{
                backgroundColor: player.id === currentPlayerId ? '#ffe082' : idx % 2 === 0 ? '#fafafa' : '#fff',
                fontWeight: player.id === currentPlayerId ? 'bold' : 'normal',
                transition: 'background 0.2s',
              }}
            >
              <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>{ranks[idx]}</td>
              <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>{player.name}</td>
              <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>{player.score}/64</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
