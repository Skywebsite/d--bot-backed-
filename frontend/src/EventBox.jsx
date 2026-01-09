import React from 'react';
import './EventBox.css';

const EventBox = ({ data }) => {
    if (!data) return null;

    const { title, date, time, host, lineup, location, description } = data;

    // Logic for Day or Night
    const isNight = (timeStr) => {
        if (!timeStr) return false;
        const timeMatch = timeStr.match(/(\d+):?(\d+)?\s*(AM|PM)/i);
        if (!timeMatch) return false;

        const hour = parseInt(timeMatch[1]);
        const isPM = timeMatch[3].toUpperCase() === 'PM';

        // Logic: Night is roughly 6 PM to 6 AM
        if (isPM) {
            return hour >= 6 || hour === 12; // 6 PM - 11 PM, 12 PM is day but 12 AM is handled below
        } else {
            return hour < 6 || hour === 12; // 12 AM - 5 AM
        }
    };

    const nightStatus = isNight(time);

    return (
        <div className="event-container">
            <div className="event-box">
                <div className="glow"></div>
                <header className="event-header">
                    <h1 className="event-title">{title}</h1>
                    <div className="event-host">Hosted by {host}</div>
                </header>

                <div className="event-details">
                    <div className="detail-item">
                        <span className="detail-label">Date</span>
                        <span className="detail-value">{date}</span>
                    </div>
                    <div className="detail-item">
                        <span className="detail-label">Time</span>
                        <span className="detail-value">{time}</span>
                    </div>
                    <div className="detail-item">
                        <span className="detail-label">Location</span>
                        <span className="detail-value">{location}</span>
                    </div>
                    <div className="detail-item">
                        <span className="detail-label">Atmosphere</span>
                        <div className={`status-badge ${nightStatus ? 'night' : ''}`}>
                            {nightStatus ? '🌙 Night Mood' : '☀️ Day Vibe'}
                        </div>
                    </div>
                </div>

                {lineup && lineup.length > 0 && (
                    <div className="lineup-section">
                        <div className="lineup-title">Lineup / DJs</div>
                        <div className="lineup-tags">
                            {lineup.map((dj, index) => (
                                <span key={index} className="lineup-tag">{dj}</span>
                            ))}
                        </div>
                    </div>
                )}

                {description && <p className="description">{description}</p>}
            </div>
        </div>
    );
};

export default EventBox;
