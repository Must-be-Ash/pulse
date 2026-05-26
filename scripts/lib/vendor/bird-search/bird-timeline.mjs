#!/usr/bin/env node
/**
 * bird-timeline.mjs - Fetch tweets from Twitter Lists and Home Timeline.
 * Uses the same Bird client infrastructure as bird-search.mjs.
 *
 * Usage:
 *   node bird-timeline.mjs --list <list_id> [--pages N] [--json]
 *   node bird-timeline.mjs --home [--pages N] [--json]
 *   node bird-timeline.mjs --bookmarks [--pages N] [--json]
 */

import { resolveCredentials } from './lib/cookies.js';
import { TwitterClientBase } from './lib/twitter-client-base.js';
import { TWITTER_API_BASE } from './lib/twitter-client-constants.js';
import { buildHomeTimelineFeatures, buildBookmarksFeatures } from './lib/twitter-client-features.js';
import { parseTweetsFromInstructions, extractCursorFromInstructions } from './lib/twitter-client-utils.js';

const args = process.argv.slice(2);

let mode = null;       // 'list' or 'home'
let listId = null;
let maxPages = 5;
let jsonOutput = false;
let pageDelayMs = 1500; // delay between pages to avoid rate limits

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--list' && args[i + 1]) {
    mode = 'list';
    listId = args[i + 1];
    i++;
  } else if (args[i] === '--home') {
    mode = 'home';
  } else if (args[i] === '--bookmarks') {
    mode = 'bookmarks';
  } else if (args[i] === '--pages' && args[i + 1]) {
    maxPages = parseInt(args[i + 1], 10);
    i++;
  } else if (args[i] === '--delay' && args[i + 1]) {
    pageDelayMs = parseInt(args[i + 1], 10);
    i++;
  } else if (args[i] === '--json') {
    jsonOutput = true;
  }
}

if (!mode) {
  process.stderr.write('Usage: node bird-timeline.mjs --list <id> [--pages N] [--json]\n');
  process.stderr.write('       node bird-timeline.mjs --home [--pages N] [--json]\n');
  process.exit(1);
}

try {
  const { cookies } = await resolveCredentials({});
  if (!cookies.authToken || !cookies.ct0) {
    process.stderr.write('Not authenticated. Set AUTH_TOKEN and CT0 env vars.\n');
    process.exit(1);
  }

  const client = new TwitterClientBase({
    cookies: { authToken: cookies.authToken, ct0: cookies.ct0 },
    timeoutMs: 30000,
  });

  const features = buildHomeTimelineFeatures();
  const allTweets = [];
  const seen = new Set();
  let cursor = undefined;

  for (let page = 0; page < maxPages; page++) {
    if (page > 0 && pageDelayMs > 0) {
      await new Promise(r => setTimeout(r, pageDelayMs));
    }

    let queryId, variables, endpoint, features_to_use;

    if (mode === 'list') {
      queryId = await client.getQueryId('ListLatestTweetsTimeline');
      endpoint = 'ListLatestTweetsTimeline';
      features_to_use = features;
      variables = {
        listId: listId,
        count: 20,
        ...(cursor ? { cursor } : {}),
      };
    } else if (mode === 'bookmarks') {
      queryId = await client.getQueryId('Bookmarks');
      endpoint = 'Bookmarks';
      features_to_use = buildBookmarksFeatures();
      variables = {
        count: 20,
        withDownvotePerspective: false,
        withReactionsMetadata: false,
        withReactionsPerspective: false,
        ...(cursor ? { cursor } : {}),
      };
    } else {
      queryId = await client.getQueryId('HomeTimeline');
      endpoint = 'HomeTimeline';
      features_to_use = features;
      variables = {
        count: 20,
        includePromotedContent: false,
        latestControlAvailable: true,
        requestContext: 'launch',
        ...(cursor ? { cursor } : {}),
      };
    }

    const params = new URLSearchParams({
      variables: JSON.stringify(variables),
      features: JSON.stringify(features_to_use),
    });

    const url = `${TWITTER_API_BASE}/${queryId}/${endpoint}?${params.toString()}`;

    const response = await client.fetchWithTimeout(url, {
      method: 'GET',
      headers: client.getHeaders(),
    });

    if (!response.ok) {
      const text = await response.text();
      process.stderr.write(`[bird-timeline] HTTP ${response.status}: ${text.slice(0, 200)}\n`);
      break;
    }

    const data = await response.json();

    // Extract instructions from the response
    let instructions;
    if (mode === 'list') {
      instructions = data.data?.list?.tweets_timeline?.timeline?.instructions;
    } else if (mode === 'bookmarks') {
      instructions = data.data?.bookmark_timeline_v2?.timeline?.instructions;
    } else {
      instructions = data.data?.home?.home_timeline_urt?.instructions;
    }

    if (!instructions) {
      process.stderr.write(`[bird-timeline] No instructions in page ${page + 1}\n`);
      break;
    }

    const tweets = parseTweetsFromInstructions(instructions, { quoteDepth: 0 });
    const newCursor = extractCursorFromInstructions(instructions);

    let added = 0;
    for (const tweet of tweets) {
      if (!seen.has(tweet.id)) {
        seen.add(tweet.id);
        allTweets.push(tweet);
        added++;
      }
    }

    process.stderr.write(`[bird-timeline] Page ${page + 1}: ${tweets.length} tweets (${added} new, ${allTweets.length} total)\n`);

    if (!newCursor || newCursor === cursor || tweets.length === 0) {
      break;
    }
    cursor = newCursor;
  }

  // Output items array — write in chunks to avoid buffer issues with large payloads
  const jsonStr = JSON.stringify(allTweets);
  const chunkSize = 16384;
  for (let i = 0; i < jsonStr.length; i += chunkSize) {
    const ok = process.stdout.write(jsonStr.slice(i, i + chunkSize));
    if (!ok) {
      await new Promise(r => process.stdout.once('drain', r));
    }
  }
  process.stdout.write('\n');
  // Wait for stdout to fully flush before exiting
  await new Promise(r => process.stdout.end(r));
  process.exit(0);

} catch (err) {
  process.stderr.write(`[bird-timeline] Error: ${err.message}\n`);
  process.stdout.write(JSON.stringify({ error: err.message, items: [] }));
  process.exit(1);
}
