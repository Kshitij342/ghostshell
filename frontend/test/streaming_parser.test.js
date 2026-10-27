import test from 'node:test';
import assert from 'node:assert/strict';
import { appendStreamContent } from '../src/services/api.js';

test('appendStreamContent appends standard chunks normally', () => {
  let content = '';
  content = appendStreamContent(content, 'Hello, ');
  content = appendStreamContent(content, 'I am GhostShell.');
  assert.equal(content, 'Hello, I am GhostShell.');
});

test('appendStreamContent prevents appending model text after deterministic explanation is complete', () => {
  // Simulate receiving the complete deterministic explanation from the backend
  let content = '> [!CAUTION]\n> Deterministic Safety Notice\n\n### Explanation of `git rm -- preview`\n\n**1. Preserve Exact Command**\n';
  
  // Model attempts to append hallucinated text afterwards
  const hallucinatedChunk = '\n\nThe command `git rm --preview` is valid and previews deletion.';
  const updatedContent = appendStreamContent(content, hallucinatedChunk);

  // Must NOT append the hallucinated model text
  assert.equal(updatedContent, content);
  assert.ok(!updatedContent.includes('git rm --preview'));
  assert.ok(!updatedContent.includes('is valid and previews deletion'));
});

test('appendStreamContent sanitizes any corrupted --preview tokens when safety notice is present', () => {
  let content = '> [!CAUTION]\n> **Deterministic Safety Notice**\n\n';
  
  // Chunk containing corrupted token
  const chunkWithCorruptedFlag = 'Do not run git rm --preview because --preview is unknown.';
  content = appendStreamContent(content, chunkWithCorruptedFlag);

  // Must sanitize git rm --preview and standalone --preview
  assert.ok(!content.includes('git rm --preview'));
  assert.ok(content.includes('git rm -- preview'));
});
