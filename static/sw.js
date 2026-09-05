// KasirToko Service Worker
// P3-7: WAJIB bump CACHE_NAME setiap deploy agar user tidak terjebak di UI basi.
// Format: kasirtoko-vYYYYMMDD-<nomor urut hari itu>
const CACHE_NAME = 'kasirtoko-v20260906-2';
const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/vendor/lucide.min.js',
  '/static/css/app.css',
  '/static/js/api.js',
  '/static/js/pendukung.js',
  '/static/js/kasir.js',
  '/static/js/produk.js',
  '/static/js/transaksi.js',
  '/static/js/laporan.js',
  '/offline'
];

// Install: cache aset statis
self.addEventListener('install', event => {
  console.log('[SW] Installing new version:', CACHE_NAME);
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate: hapus cache lama
self.addEventListener('activate', event => {
  console.log('[SW] Activating:', CACHE_NAME);
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => {
        console.log('[SW] Deleting old cache:', k);
        return caches.delete(k);
      }))
    )
  );
  self.clients.claim();
});

// Fetch: strategi Network First untuk API, Cache First untuk aset statis
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API calls: selalu ke network, jangan cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(JSON.stringify({ error: 'Tidak ada koneksi ke server' }), {
          headers: { 'Content-Type': 'application/json' }
        })
      )
    );
    return;
  }

  // Halaman utama & aset: Network First, fallback ke cache
  event.respondWith(
    fetch(event.request)
      .then(res => {
        // Simpan ke cache jika berhasil
        if (res.ok && event.request.method === 'GET') {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return res;
      })
      .catch(() =>
        caches.match(event.request).then(cached =>
          cached || caches.match('/offline')
        )
      )
  );
});
