const CACHE = "planner-shell-v1";
self.addEventListener("install", (event) => event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(["/", "/login"]))));
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
self.addEventListener("push", (event) => {
  const data = event.data ? event.data.json() : {title:"AI Planner", body:"Новое напоминание", url:"/today"};
  event.waitUntil(self.registration.showNotification(data.title, {body:data.body, tag:data.tag, icon:"/icon.svg", data:{url:data.url || "/today"}}));
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data?.url || "/today"));
});
