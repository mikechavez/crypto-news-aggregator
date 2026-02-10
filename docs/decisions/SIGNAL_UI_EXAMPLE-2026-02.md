# Signal-to-Narrative Linking - UI Examples

## Signal Card with Narratives

```
┌─────────────────────────────────────────────────────────┐
│ #1 Bitcoin $BTC                              85%        │
├─────────────────────────────────────────────────────────┤
│ Type:        [Cryptocurrency]                           │
│ Velocity:    12.5 mentions/hr                           │
│ Sources:     8 sources                                  │
│ Sentiment:   Positive                                   │
│ Last Updated: 5 minutes ago                             │
│ ─────────────────────────────────────────────────────── │
│ Part of:                                                │
│ [Regulatory] [Institutional Investment]                 │
│ └─ clickable badges, color-coded by theme               │
└─────────────────────────────────────────────────────────┘
```

## Emerging Signal Card

```
┌─────────────────────────────────────────────────────────┐
│ #5 NewProtocol                               42%        │
├─────────────────────────────────────────────────────────┤
│ Type:        [Project]                                  │
│ Velocity:    3.2 mentions/hr                            │
│ Sources:     4 sources                                  │
│ Sentiment:   Neutral                                    │
│ Last Updated: 2 minutes ago                             │
│ ─────────────────────────────────────────────────────── │
│ 🆕 Emerging  Not yet part of any narrative              │
│ └─ yellow badge indicating new/unclassified signal      │
└─────────────────────────────────────────────────────────┘
```

## Theme Badge Colors

- **Regulatory**: Red background (text-red-700 bg-red-100)
- **DeFi Adoption**: Purple background (text-purple-700 bg-purple-100)
- **Institutional Investment**: Green background (text-green-700 bg-green-100)
- **Technology Upgrade**: Blue background (text-blue-700 bg-blue-100)
- **Market Volatility**: Orange background (text-orange-700 bg-orange-100)
- **Security**: Red background (text-red-700 bg-red-100)
- **Partnership**: Indigo background (text-indigo-700 bg-indigo-100)
- **Ecosystem Growth**: Teal background (text-teal-700 bg-teal-100)

## User Interactions

1. **Hover over theme badge**: Shows full narrative title in tooltip
2. **Click theme badge**: Navigates to /narratives page (filtered view coming in future)
3. **Emerging badge**: Static indicator, helps users spot new trends

## Responsive Design

- On mobile: Theme badges wrap to multiple lines
- On desktop: Badges display inline with proper spacing
- All badges have hover effects for better UX
