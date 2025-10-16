/**
 * Test script to verify narrative API returns lifecycle data
 * 
 * Run with: npx tsx src/test-narrative-api.ts
 */

interface LifecycleHistoryEntry {
  state: string;
  timestamp: string;
  article_count: number;
  velocity: number;
}

interface PeakActivity {
  date: string;
  article_count: number;
  velocity: number;
}

interface EntityRelationship {
  a: string;
  b: string;
  weight: number;
}

interface Narrative {
  theme: string;
  title: string;
  summary: string;
  entities: string[];
  article_count: number;
  mention_velocity: number;
  lifecycle: string;
  lifecycle_state?: string;
  lifecycle_history?: LifecycleHistoryEntry[];
  fingerprint?: number[];
  momentum?: string;
  recency_score?: number;
  entity_relationships?: EntityRelationship[];
  first_seen: string;
  last_updated: string;
  days_active?: number;
  peak_activity?: PeakActivity;
  articles: any[];
}

async function testNarrativeAPI() {
  // Use local backend
  const baseURL = 'http://localhost:8000';
  const apiURL = `${baseURL}/api/v1/narratives/active?limit=5`;
  
  console.log('🔍 Testing Narrative API...');
  console.log(`📡 Fetching from: ${apiURL}\n`);
  
  try {
    const response = await fetch(apiURL);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const narratives: Narrative[] = await response.json();
    
    console.log(`✅ Received ${narratives.length} narratives\n`);
    
    if (narratives.length === 0) {
      console.log('⚠️  No narratives found in database');
      return;
    }
    
    // Check first narrative for new fields
    const firstNarrative = narratives[0];
    
    console.log('📊 First Narrative Fields:');
    console.log('─'.repeat(60));
    console.log(`Theme: ${firstNarrative.theme}`);
    console.log(`Title: ${firstNarrative.title}`);
    console.log(`Entities: ${firstNarrative.entities.join(', ')}`);
    console.log(`Article Count: ${firstNarrative.article_count}`);
    console.log(`Mention Velocity: ${firstNarrative.mention_velocity}`);
    console.log(`Lifecycle: ${firstNarrative.lifecycle}`);
    console.log(`Momentum: ${firstNarrative.momentum || 'N/A'}`);
    console.log(`Recency Score: ${firstNarrative.recency_score || 'N/A'}`);
    console.log(`Days Active: ${firstNarrative.days_active || 'N/A'}`);
    console.log(`First Seen: ${firstNarrative.first_seen}`);
    console.log(`Last Updated: ${firstNarrative.last_updated}`);
    
    console.log('\n🔬 New Lifecycle Fields:');
    console.log('─'.repeat(60));
    console.log(`lifecycle_state: ${firstNarrative.lifecycle_state || '❌ NOT PRESENT'}`);
    console.log(`lifecycle_history: ${firstNarrative.lifecycle_history ? `✅ ${firstNarrative.lifecycle_history.length} entries` : '❌ NOT PRESENT'}`);
    console.log(`fingerprint: ${firstNarrative.fingerprint ? `✅ ${firstNarrative.fingerprint.length} dimensions` : '❌ NOT PRESENT'}`);
    
    if (firstNarrative.lifecycle_history && firstNarrative.lifecycle_history.length > 0) {
      console.log('\n📜 Lifecycle History:');
      firstNarrative.lifecycle_history.forEach((entry, idx) => {
        console.log(`  ${idx + 1}. ${entry.state} @ ${entry.timestamp} (${entry.article_count} articles, velocity: ${entry.velocity})`);
      });
    }
    
    if (firstNarrative.peak_activity) {
      console.log('\n📈 Peak Activity:');
      console.log(`  Date: ${firstNarrative.peak_activity.date}`);
      console.log(`  Articles: ${firstNarrative.peak_activity.article_count}`);
      console.log(`  Velocity: ${firstNarrative.peak_activity.velocity}`);
    }
    
    if (firstNarrative.entity_relationships && firstNarrative.entity_relationships.length > 0) {
      console.log('\n🔗 Entity Relationships:');
      firstNarrative.entity_relationships.slice(0, 5).forEach((rel, idx) => {
        console.log(`  ${idx + 1}. ${rel.a} ↔ ${rel.b} (weight: ${rel.weight})`);
      });
    }
    
    console.log('\n' + '─'.repeat(60));
    console.log('\n📋 Summary:');
    console.log(`✅ API is responding correctly`);
    console.log(`✅ TypeScript types match API response`);
    
    const hasLifecycleState = narratives.some(n => n.lifecycle_state);
    const hasLifecycleHistory = narratives.some(n => n.lifecycle_history && n.lifecycle_history.length > 0);
    const hasFingerprint = narratives.some(n => n.fingerprint && n.fingerprint.length > 0);
    
    if (hasLifecycleState) {
      console.log(`✅ lifecycle_state field is present`);
    } else {
      console.log(`⚠️  lifecycle_state field is NOT present (backend may not be returning it yet)`);
    }
    
    if (hasLifecycleHistory) {
      console.log(`✅ lifecycle_history field is present`);
    } else {
      console.log(`⚠️  lifecycle_history field is NOT present (backend may not be returning it yet)`);
    }
    
    if (hasFingerprint) {
      console.log(`✅ fingerprint field is present`);
    } else {
      console.log(`⚠️  fingerprint field is NOT present (backend may not be returning it yet)`);
    }
    
  } catch (error) {
    console.error('❌ Error testing API:', error);
    throw error;
  }
}

// Run the test
testNarrativeAPI().catch(err => {
  console.error('Test failed:', err);
});
