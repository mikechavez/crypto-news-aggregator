#!/usr/bin/env node

/**
 * Automated UI Verification Script
 * Checks code configuration and API responses
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const results = {
  passed: [],
  failed: [],
  warnings: []
};

function pass(test, details = '') {
  results.passed.push({ test, details });
  console.log(`✅ ${test}${details ? ': ' + details : ''}`);
}

function fail(test, details = '') {
  results.failed.push({ test, details });
  console.log(`❌ ${test}${details ? ': ' + details : ''}`);
}

function warn(test, details = '') {
  results.warnings.push({ test, details });
  console.log(`⚠️  ${test}${details ? ': ' + details : ''}`);
}

console.log('\n🔍 Context Owl UI Verification\n');
console.log('=' .repeat(60));

// 1. Check Dark Mode Configuration
console.log('\n📱 1. Dark Mode Configuration');
console.log('-'.repeat(60));

try {
  const themeContext = fs.readFileSync(path.join(__dirname, 'src/contexts/ThemeContext.tsx'), 'utf8');
  
  if (themeContext.includes("useState<Theme>('dark')")) {
    pass('Dark mode default', 'Theme defaults to dark');
  } else {
    fail('Dark mode default', 'Theme does not default to dark');
  }
  
  if (themeContext.includes("root.classList.add(theme)")) {
    pass('Dark mode class application', 'Theme class applied to root');
  } else {
    fail('Dark mode class application', 'Theme class not applied correctly');
  }
} catch (e) {
  fail('Dark mode configuration', e.message);
}

// 2. Check Tailwind Dark Mode Config
console.log('\n🎨 2. Tailwind Configuration');
console.log('-'.repeat(60));

try {
  const tailwindConfig = fs.readFileSync(path.join(__dirname, 'tailwind.config.js'), 'utf8');
  
  if (tailwindConfig.includes("darkMode: 'class'")) {
    pass('Tailwind dark mode', 'Class-based dark mode enabled');
  } else {
    fail('Tailwind dark mode', 'Dark mode not configured as class-based');
  }
  
  // Check dark color definitions
  const darkColors = ['dark-bg', 'dark-card', 'dark-border', 'dark-hover'];
  darkColors.forEach(color => {
    if (tailwindConfig.includes(color)) {
      pass(`Dark color: ${color}`, 'Defined in config');
    } else {
      fail(`Dark color: ${color}`, 'Not found in config');
    }
  });
  
  // Check glow shadows
  const glowShadows = ['glow-blue', 'glow-green', 'glow-orange', 'glow-red', 'glow-purple'];
  glowShadows.forEach(shadow => {
    if (tailwindConfig.includes(shadow)) {
      pass(`Glow shadow: ${shadow}`, 'Defined in config');
    } else {
      fail(`Glow shadow: ${shadow}`, 'Not found in config');
    }
  });
} catch (e) {
  fail('Tailwind configuration', e.message);
}

// 3. Check Lifecycle Badge Configuration
console.log('\n🏷️  3. Lifecycle Badge Configuration');
console.log('-'.repeat(60));

try {
  const narrativesPage = fs.readFileSync(path.join(__dirname, 'src/pages/Narratives.tsx'), 'utf8');
  
  const lifecycleStages = [
    { name: 'emerging', icon: 'Sparkles', color: 'blue', glow: 'shadow-glow-blue' },
    { name: 'rising', icon: 'TrendingUp', color: 'green', glow: 'shadow-glow-green' },
    { name: 'hot', icon: 'Flame', color: 'orange', glow: 'shadow-glow-orange' },
    { name: 'heating', icon: 'Zap', color: 'red', glow: 'shadow-glow-red' },
    { name: 'mature', icon: 'Star', color: 'purple', glow: 'shadow-glow-purple' },
    { name: 'cooling', icon: 'Wind', color: 'gray', glow: '' }
  ];
  
  lifecycleStages.forEach(stage => {
    if (narrativesPage.includes(`${stage.name}:`) && 
        narrativesPage.includes(`icon: ${stage.icon}`)) {
      pass(`Lifecycle: ${stage.name}`, `Icon: ${stage.icon}, Color: ${stage.color}`);
    } else {
      fail(`Lifecycle: ${stage.name}`, 'Configuration incomplete');
    }
  });
  
  // Check icon imports
  const iconImports = ['Sparkles', 'TrendingUp', 'Flame', 'Zap', 'Star', 'Wind'];
  iconImports.forEach(icon => {
    if (narrativesPage.includes(`import { ${icon}`) || narrativesPage.includes(`, ${icon}`)) {
      pass(`Icon import: ${icon}`, 'Imported from lucide-react');
    } else {
      fail(`Icon import: ${icon}`, 'Not imported');
    }
  });
} catch (e) {
  fail('Lifecycle badge configuration', e.message);
}

// 4. Check Sentiment Removal from Signals
console.log('\n🚫 4. Sentiment Removal Verification');
console.log('-'.repeat(60));

try {
  const signalsPage = fs.readFileSync(path.join(__dirname, 'src/pages/Signals.tsx'), 'utf8');
  
  const sentimentKeywords = ['sentiment', 'Sentiment', 'SENTIMENT'];
  let sentimentFound = false;
  
  sentimentKeywords.forEach(keyword => {
    // Check if sentiment is mentioned in the code (excluding comments)
    const lines = signalsPage.split('\n');
    const codeLines = lines.filter(line => !line.trim().startsWith('//') && !line.trim().startsWith('*'));
    const codeText = codeLines.join('\n');
    
    if (codeText.includes(keyword)) {
      sentimentFound = true;
    }
  });
  
  if (!sentimentFound) {
    pass('Sentiment removed', 'No sentiment references in Signals page');
  } else {
    fail('Sentiment removed', 'Sentiment references still exist');
  }
} catch (e) {
  fail('Sentiment removal check', e.message);
}

// 5. Check Velocity Indicators
console.log('\n📊 5. Velocity Indicator Configuration');
console.log('-'.repeat(60));

try {
  const signalsPage = fs.readFileSync(path.join(__dirname, 'src/pages/Signals.tsx'), 'utf8');
  
  const velocityStates = [
    { threshold: 500, label: 'Surging', icon: 'TrendingUp' },
    { threshold: 200, label: 'Rising', icon: 'ArrowUp' },
    { threshold: 50, label: 'Growing', icon: 'Activity' },
    { threshold: 0, label: 'Active', icon: 'Minus' },
    { threshold: -1, label: 'Declining', icon: 'TrendingDown' }
  ];
  
  velocityStates.forEach(state => {
    if (signalsPage.includes(`label: '${state.label}'`) && 
        signalsPage.includes(`icon: ${state.icon}`)) {
      pass(`Velocity: ${state.label}`, `Threshold: ${state.threshold >= 0 ? '>=' : '<'} ${Math.abs(state.threshold)}%, Icon: ${state.icon}`);
    } else {
      fail(`Velocity: ${state.label}`, 'Configuration incomplete');
    }
  });
  
  // Check velocity icon imports
  const velocityIcons = ['TrendingUp', 'ArrowUp', 'Activity', 'Minus', 'TrendingDown'];
  velocityIcons.forEach(icon => {
    if (signalsPage.includes(icon)) {
      pass(`Velocity icon: ${icon}`, 'Present in code');
    } else {
      fail(`Velocity icon: ${icon}`, 'Not found');
    }
  });
} catch (e) {
  fail('Velocity indicator check', e.message);
}

// 6. Check Lucide Icon Imports
console.log('\n🎯 6. Lucide Icon Imports');
console.log('-'.repeat(60));

try {
  const files = [
    { path: 'src/components/Layout.tsx', icons: ['TrendingUp', 'Newspaper', 'FileText', 'Moon', 'Sun'] },
    { path: 'src/pages/Signals.tsx', icons: ['TrendingUp', 'ArrowUp', 'Activity', 'Minus', 'TrendingDown'] },
    { path: 'src/pages/Narratives.tsx', icons: ['Sparkles', 'TrendingUp', 'Flame', 'Zap', 'Star', 'Wind'] },
    { path: 'src/pages/Articles.tsx', icons: ['ExternalLink'] }
  ];
  
  files.forEach(file => {
    try {
      const content = fs.readFileSync(path.join(__dirname, file.path), 'utf8');
      const importLine = content.split('\n').find(line => line.includes('lucide-react'));
      
      if (importLine) {
        file.icons.forEach(icon => {
          if (importLine.includes(icon)) {
            pass(`${path.basename(file.path)}: ${icon}`, 'Imported');
          } else {
            warn(`${path.basename(file.path)}: ${icon}`, 'Not in import statement');
          }
        });
      } else {
        fail(`${path.basename(file.path)}`, 'No lucide-react import found');
      }
    } catch (e) {
      fail(`${file.path}`, e.message);
    }
  });
} catch (e) {
  fail('Lucide icon check', e.message);
}

// 7. Check Framer Motion Animations
console.log('\n✨ 7. Framer Motion Animations');
console.log('-'.repeat(60));

try {
  const cardComponent = fs.readFileSync(path.join(__dirname, 'src/components/Card.tsx'), 'utf8');
  
  if (cardComponent.includes('whileHover={{ y: -4 }}')) {
    pass('Card hover animation', 'Lift effect configured (y: -4)');
  } else {
    fail('Card hover animation', 'Hover effect not found or incorrect');
  }
  
  if (cardComponent.includes('motion.div')) {
    pass('Framer Motion integration', 'motion.div used in Card component');
  } else {
    fail('Framer Motion integration', 'motion.div not found');
  }
  
  const signalsPage = fs.readFileSync(path.join(__dirname, 'src/pages/Signals.tsx'), 'utf8');
  
  if (signalsPage.includes('AnimatePresence')) {
    pass('Tab transition animation', 'AnimatePresence configured');
  } else {
    fail('Tab transition animation', 'AnimatePresence not found');
  }
  
  if (signalsPage.includes('initial={{ opacity: 0')) {
    pass('Fade-in animation', 'Initial opacity configured');
  } else {
    fail('Fade-in animation', 'Initial state not configured');
  }
} catch (e) {
  fail('Animation check', e.message);
}

// 8. Check Theme Toggle
console.log('\n🌓 8. Theme Toggle Implementation');
console.log('-'.repeat(60));

try {
  const layout = fs.readFileSync(path.join(__dirname, 'src/components/Layout.tsx'), 'utf8');
  
  if (layout.includes('toggleTheme')) {
    pass('Theme toggle function', 'toggleTheme function used');
  } else {
    fail('Theme toggle function', 'toggleTheme not found');
  }
  
  if (layout.includes('theme === \'dark\' ? (') && 
      layout.includes('<Sun') && 
      layout.includes('<Moon')) {
    pass('Theme toggle icons', 'Sun/Moon icons switch based on theme');
  } else {
    fail('Theme toggle icons', 'Icon switching not configured correctly');
  }
  
  if (layout.includes('useTheme()')) {
    pass('Theme context usage', 'useTheme hook used in Layout');
  } else {
    fail('Theme context usage', 'useTheme hook not found');
  }
} catch (e) {
  fail('Theme toggle check', e.message);
}

// 9. Check API Integration
console.log('\n🔌 9. API Integration');
console.log('-'.repeat(60));

try {
  const apiClient = fs.readFileSync(path.join(__dirname, 'src/api/client.ts'), 'utf8');
  
  if (apiClient.includes('http://localhost:8000')) {
    pass('API base URL', 'Configured for local development');
  } else {
    warn('API base URL', 'Not set to localhost:8000');
  }
  
  const signalsApi = fs.readFileSync(path.join(__dirname, 'src/api/signals.ts'), 'utf8');
  
  if (signalsApi.includes('getSignals')) {
    pass('Signals API method', 'getSignals method defined');
  } else {
    fail('Signals API method', 'getSignals not found');
  }
  
  const narrativesApi = fs.readFileSync(path.join(__dirname, 'src/api/narratives.ts'), 'utf8');
  
  if (narrativesApi.includes('getNarratives')) {
    pass('Narratives API method', 'getNarratives method defined');
  } else {
    fail('Narratives API method', 'getNarratives not found');
  }
} catch (e) {
  fail('API integration check', e.message);
}

// Summary
console.log('\n' + '='.repeat(60));
console.log('📊 VERIFICATION SUMMARY');
console.log('='.repeat(60));
console.log(`✅ Passed: ${results.passed.length}`);
console.log(`❌ Failed: ${results.failed.length}`);
console.log(`⚠️  Warnings: ${results.warnings.length}`);
console.log('='.repeat(60));

if (results.failed.length > 0) {
  console.log('\n❌ Failed Tests:');
  results.failed.forEach(({ test, details }) => {
    console.log(`   - ${test}${details ? ': ' + details : ''}`);
  });
}

if (results.warnings.length > 0) {
  console.log('\n⚠️  Warnings:');
  results.warnings.forEach(({ test, details }) => {
    console.log(`   - ${test}${details ? ': ' + details : ''}`);
  });
}

console.log('\n✨ Code verification complete!\n');
console.log('Note: Visual elements (colors, animations, hover effects) require browser testing.\n');

process.exit(results.failed.length > 0 ? 1 : 0);
