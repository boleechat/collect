import fetch from 'node-fetch';
import fs from 'fs';

const SRC = [
  {
    name: '央视频',
    url: 'http://bolee.eu.org:56845/ysp.m3u'
  },
  {
    name: 'MyTVSuper',
    url: 'http://bolee.eu.org:56845/mytvsuper-tivimate.m3u',
    mod: (noproxy) => noproxy ? identity : proxify
  },
  {
    name: '四季',
    url: 'http://bolee.eu.org:56845/4gtv.m3u',
    mod: (noproxy) => noproxy ? identity : proxify
  },
  {
    name: '油管',
    url: 'http://bolee.eu.org:56845/youtube/list/你自己的YouTube播放列表',
    mod: (noproxy) => noproxy ? identity : proxify
  }
];

const PROXY_DOMAINS = [
  'http://bolee.eu.org',
  '[^/]+\\.hinet\\.net',
  '[^/]+\\.litv\\.4gtv',
  '[^/]+\\.litv\\.litv',
  '[^/]+\\.4gtv\\.',
  '[^/]+\\.googlevideo\\.com',
  '[^/]+\\.tvb.com(:\\d+)?'
];

function identity(it) { return it; }

function proxify(it) {
  for (const dom of PROXY_DOMAINS) {
    it = it.replace(new RegExp('https?://' + dom, 'g'), process.env.PROXY_URL + '/$&');
  }
  return it;
}

async function fetchWithRetry(url, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, { timeout: 10000 });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.text();
    } catch (e) {
      console.error(`Attempt ${i + 1} failed: ${e.message}`);
      if (i === retries - 1) throw e;
      await new Promise(r => setTimeout(r, 5000)); // Wait 5 seconds before retrying
    }
  }
}

async function fetchPlaylist() {
  let text = `#EXTM3U
#EXTM3U x-tvg-url="https://assets.livednow.com/epg.xml"

`;
  for (const src of SRC) {
    console.log(`Fetching playlist from ${src.name}: ${src.url}`);
    try {
      let respText = await fetchWithRetry(src.url);
      console.log(`Received ${respText.length} bytes from ${src.name}`);
      let channels = respText.split(/^#EXT/gm).map(it => '#EXT' + it).filter(it => it.startsWith('#EXTINF'));
      console.log(`Found ${channels.length} channels in ${src.name}`);
      if (src.mod) {
        channels = channels.map(src.mod(false));
        console.log(`Applied modification to ${src.name}`);
      }
      text += channels.join('\n');
    } catch (error) {
      console.error(`Error fetching ${src.name}: ${error.message}`);
      // Continue with the next source instead of stopping entirely
    }
  }
  return text;
}

fetchPlaylist().then(playlist => {
  fs.writeFileSync('playlist.m3u', playlist);
  console.log('Playlist updated successfully');
  if (process.env.TEST_MODE === 'true') {
    console.log('Test mode: Playlist content:');
    console.log(playlist);
  }
}).catch(error => {
  console.error('Error updating playlist:', error);
  process.exit(1);
});
