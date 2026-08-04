const CACHE = "planner-shell-v1";
self.addEventListener("install", (event) => event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(["/", "/login"]))));
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
self.addEventListener("push", (event) => {
  const payload = event.data ? event.data.json() : {};
  const data = payload.notification || payload;
  event.waitUntil(self.registration.showNotification(data.title || "AI Planner", {body:data.body || "Новое напоминание", tag:data.tag, icon:"/icon.svg", data:{url:data.navigate || data.url || "/today"}}));
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data?.url || "/today"));
});
