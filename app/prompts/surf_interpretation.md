# Surf Conditions Interpretation Guide

This guide helps interpret surf forecast data returned by the `get_surf_conditions` tool.

## Wave Height Scale

| Height (m) | Category | Suitable For |
|------------|----------|--------------|
| 0 - 0.5m | Flat | Not surfable |
| 0.5 - 1m | Small | Beginners, longboards |
| 1 - 1.5m | Medium-Small | All skill levels |
| 1.5 - 2m | Medium | Intermediate to advanced |
| 2 - 3m | Large | Experienced surfers |
| 3m+ | Very Large | Expert surfers only |

## Wave Period Interpretation

The wave period indicates the time between consecutive wave crests:

| Period (s) | Type | Quality |
|------------|------|---------|
| < 8s | Wind swell | Poor - Messy, disorganized waves |
| 8 - 10s | Short period swell | Fair - Acceptable wave shape |
| 10 - 12s | Medium period swell | Good - Well-formed waves |
| 12 - 16s | Ground swell | Excellent - Clean, powerful waves |
| 16s+ | Long period ground swell | Premium - Best quality waves |

**Key insight**: Higher period = more energy = better wave quality. Ground swell (12s+) travels long distances and produces cleaner, more organized waves.

## Wind Type Analysis

### Offshore Wind (Best)
- Wind blows from land toward the ocean
- Creates clean, glassy wave faces
- Holds waves up longer before breaking
- Best conditions for surfing

### Cross-shore Wind (Moderate)
- Wind blows parallel to the beach
- Acceptable with light winds (< 15 km/h)
- Can create bumpy conditions with stronger winds

### Onshore Wind (Poor)
- Wind blows from ocean toward land
- Creates choppy, disorganized waves
- Waves crumble rather than peel
- Generally poor surfing conditions

## Quality Indicators

### is_offshore
- `true`: Offshore or cross-offshore wind - favorable conditions
- `false`: Onshore or cross-onshore wind - less favorable

### good_period
- `true`: Wave period >= 10 seconds - quality swell
- `false`: Wave period < 10 seconds - wind swell or short period

### surfable
- `true`: Conditions meet minimum requirements (height >= 0.5m, period >= 8s)
- `false`: Below minimum surfing thresholds

## Swell Direction

Swell direction indicates where waves are coming FROM:
- 0° / 360° = North
- 90° = East
- 180° = South
- 270° = West

Match swell direction with beach orientation for best results:
- Beach facing the swell direction receives maximum wave energy
- Angled swells may work better for point breaks

## Wind Speed Guidelines

| Speed (m/s) | km/h | Conditions |
|-------------|------|------------|
| 0 - 3 | 0 - 11 | Light - Glassy conditions possible |
| 3 - 5 | 11 - 18 | Light - Still manageable |
| 5 - 8 | 18 - 29 | Moderate - Starting to affect waves |
| 8 - 12 | 29 - 43 | Fresh - Significant impact |
| 12+ | 43+ | Strong - Difficult conditions |

## Best Conditions Summary

Ideal surf conditions typically include:
1. **Wave height**: 1-2m (adjustable to skill level)
2. **Period**: 10+ seconds (ground swell)
3. **Wind**: Offshore, < 5 m/s
4. **Tide**: Depends on specific spot

## Example Interpretation

```json
{
  "wave_height_m": 1.5,
  "wave_period_s": 12.0,
  "wind_speed_ms": 3.2,
  "wind_type": "offshore",
  "quality_indicators": {
    "is_offshore": true,
    "good_period": true,
    "surfable": true
  }
}
```

**Interpretation**: "Excellent conditions. Medium-sized waves (1.5m) with quality ground swell (12s period). Light offshore winds will create clean, glassy wave faces. Suitable for intermediate to advanced surfers."

## Important Notes

1. **Local knowledge matters**: These are general guidelines. Local breaks may behave differently.
2. **Tides**: Forecast doesn't include tide data. Some spots only work at certain tides.
3. **Crowds**: Popular spots with good conditions will be crowded.
4. **Safety**: Always assess conditions in person before entering the water.
5. **GFS Wave coverage**: Data not available for Hudson Bay, Black Sea, Caspian Sea, and Arctic Ocean.
