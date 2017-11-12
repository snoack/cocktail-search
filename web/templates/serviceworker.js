var assetCacheName = 'assets:{{ get_assets_checksum() }}';
var dataCacheName = null;

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(cacheNames.map(function(cacheName) {
        if (!cacheName.startsWith('data:') && cacheName != assetCacheName)
          return caches.delete(cacheName);
      }));
    }).then(function() {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function(event) {
  var request = event.request;
  var url = new URL(request.url);

  if (url.origin + url.pathname == '{{ site_url }}recipes')
    // Caching strategy for recipe queries:
    // 1. If the request has been cached for current version of the index
    //    (as indicated by the Last-Modified header in the last response),
    //    deliver response from cache without hiting the server.
    // 2. Otherwise, ask the server and cache the response for future requests.
    // 3. If the request fails (e.g. if offline), fall back to
    //    all caches including those for outdated index versions.
    event.respondWith(caches.match(request, {cacheName: dataCacheName}).then(
        function(response) {
          return response || fetch(request).then(
            function(response) {
              // Don't touch the cache if the response indicates an error.
              // Return the erroneous response, don't cache it, neither use
              // nor delete a successful response from an outdated cache.
              if (!response.ok)
                return response;

              var lastModified = response.headers.get('Last-Modified');
              var timestamp = new Date(lastModified || '').getTime();
              var activeCacheName = 'data:' + timestamp;
              if (!isNaN(timestamp))
                dataCacheName = activeCacheName;
              else {
                // If the server (unexpectedly) doesn't send a
                // (valid) Last-Modified header, the response
                // will only be used to satify requests when offline.
                dataCacheName = null;
                console.warning('Missing or invalid "Last-Modified" header, ' +
                                'response is only used from cache when offline.')
              }

              // Delete any cached reponse for this request from caches for
              // outdated index versions. Note that if multiple caches have a
              // matching response, caches.match() returns the response from
              // the cache that was created first, i.e. the oldest index.
              // Regardless, it is a good practice to keep our caches clean.
              caches.keys().then(function(cacheNames) {
                cacheNames.forEach(function(cacheName) {
                  if (cacheName.startsWith('data:') &&
                      cacheName != activeCacheName)
                    caches.open(cacheName).then(function(cache) {
                      cache.delete(request).then(function(deleted) {
                        if (deleted)
                          cache.keys().then(function(requests) {
                            if (requests.length == 0)
                              caches.delete(cacheName);
                          });
                      });
                    });
                });
              });

              // Don't cache empty responses (i.e: "[]"; empty JSON array).
              // Even if offline, the UX is the same; i.e. the list is cleared,
              // either as the result of an empty response or failing request.
              var contentLength = parseInt(response.headers.get('Content-Length'));
              if (isNaN(contentLength))
                console.warning('Missing or invalid "Content-Length" header, ' +
                                'response is not cached.')
              else if (contentLength > 2) {
                var clonedResponse = response.clone();
                caches.open(activeCacheName).then(function(cache) {
                  cache.put(request, clonedResponse);
                });
              }

              return response;
            },
            function() {
              return caches.match(request);
            }
          );
        }
    ));
  else
    // For all other requests, query caches first (assets should
    // be delivered from there), and fall back to the network.
    event.respondWith(caches.match(request).then(function(response) {
      return response || fetch(request);
    }));
});
