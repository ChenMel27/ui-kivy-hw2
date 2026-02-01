# NASA TLX Workload Assessment Application

## Overview
This is a Kivy implementation of the NASA Task Load Index (TLX) workload assessment tool. The application guides users through a subjective workload assessment with pairwise factor comparisons and scale ratings.

## Requirements
- Python 3.11.x
- Kivy library

## Installation
```bash
pip install kivy
```

## Running the Application
```bash
python3 main.py
```

## Features

### Display/Device Independent Rendering
- Uses kivy_config_helper for display density simulation support
- All measurements use dp() for proper scaling across different display densities
- Window resolution: 800x600
- Window resizing is disabled

### Application Flow

#### 1. Scale Weight Phase (Pairwise Comparisons)
- Presents 15 randomized pairs of workload factors
- Randomization includes both pair order and order within pairs
- No default selection - user must choose one factor from each pair
- Selection is visually highlighted in blue
- Auto-advances to next screen upon selection
- Next button is disabled until a selection is made
- Previous button allows navigation back (except on first screen)

#### 2. Scale Value Phase
- Six custom-drawn scale widgets for rating each dimension (0-100)
- Custom Canvas rendering with:
  - Tick marks every 5 units
  - Midpoint marked with taller line
  - Colored bar showing current value
  - Visual indication when scale has been visited (blue background and border)
- Mouse interaction:
  - Click to set value
  - Click and drag for continuous adjustment
  - Values snap to increments of 5
- Zero is a valid selection
- Next button disabled until all scales have been rated

#### 3. Results Screen
- Displays for each dimension:
  - Tally (count of times selected in comparisons)
  - Weight (normalized tally value)
  - Rating (0-100 scale value)
- Calculates and displays Overall Workload Score
- No navigation buttons (end of assessment)

### Design Elements
- Clean, professional interface
- Consistent color scheme (blue: #3380CC for selections)
- Clear visual feedback for interactions
- Proper spacing and alignment throughout
- All screens preserve state when navigating

## Implementation Details

### Key Classes
- **ScaleWidget**: Custom widget with Canvas drawing for numerical scales
- **PairComparisonScreen**: Screen for pairwise factor comparisons  
- **ScaleValueScreen**: Screen for rating all six dimensions
- **ResultsScreen**: Final screen displaying calculated results
- **NASATLXApp**: Main application class managing screen flow

### Workload Factors
1. Mental Demand
2. Physical Demand
3. Temporal Demand
4. Performance (Failure → Perfect)
5. Effort
6. Frustration

### Calculations
- Weight = Tally / Total number of comparisons (15)
- Workload Score = Σ(Rating × Weight) for all dimensions

## File Structure
- main.py - Complete application code including kivy_config_helper
- README.md - This file
- kivy_config.ini - Auto-generated Kivy configuration file

## Notes
- Simulation mode is turned OFF in submitted code
- Performance scale goes from "Failure" to "Perfect" (left to right) per GT research recommendations
- Randomization occurs once per application run and is preserved when navigating between screens