const DATA_URL = "data/geo_album.json";

const formatBool = (value) => (value ? "是" : "否");

const setImage = (selector, src, fallbackText) => {
  const img = document.querySelector(selector);
  if (!img) return;
  if (src) {
    img.src = src;
  } else {
    img.replaceWith(Object.assign(document.createElement("div"), { className: "empty", textContent: fallbackText }));
  }
};

const statCard = (label, value) => `
  <article class="stat-card">
    <span class="eyebrow">${label}</span>
    <strong>${value}</strong>
  </article>
`;

const renderStats = (stats = {}) => {
  document.querySelector("#statsGrid").innerHTML = [
    statCard("总照片数", stats.photoCount ?? 0),
    statCard("GPS 照片", stats.gpsPhotoCount ?? 0),
    statCard("生成点位", stats.stopCount ?? 0),
    statCard("逆地理编码", formatBool(stats.hasAmapReverseGeocode)),
    statCard("静态地图", formatBool(stats.hasAmapStaticMap)),
    statCard("API 调用", stats.apiCallCount ?? 0),
  ].join("");

  document.querySelector("#heroPhotoCount").textContent = `${stats.photoCount ?? 0} photos`;
  document.querySelector("#heroStopCount").textContent = `${stats.stopCount ?? 0} stops`;
};

const renderMapComparison = (album) => {
  const amap = album.stats?.hasAmapStaticMap ? album.map?.amapStatic : album.map?.fallbackPng || album.map?.fallback;
  const styled = album.map?.fallback || album.map?.fallbackPng || album.map?.amapStatic;
  setImage("#amapRouteMap", amap, "暂无原始高德地图底图");
  setImage("#styledRouteMap", styled, "暂无风格化路线图");
  document.querySelector("#mapNote").textContent = album.map?.note || "地图结果已缓存，本页不在前端请求高德 API。";
};

const renderStops = (stops = []) => {
  const target = document.querySelector("#stopsList");
  if (!stops.length) {
    target.innerHTML = '<div class="empty">暂无 GPS 点位。请补充带 GPS 的照片或手动维护 stop。</div>';
    return;
  }
  target.innerHTML = stops
    .map((stop) => {
      const pois = (stop.pois || []).map((poi) => `<span>${poi.name}${poi.distance ? ` · ${poi.distance}m` : ""}</span>`).join("");
      const photos = (stop.photos || []).map((photo) => `<img src="${photo.src}" alt="${photo.filename || stop.name}" loading="lazy" />`).join("");
      return `
        <article class="stop-card">
          <div class="stop-number">${String(stop.order).padStart(2, "0")}</div>
          <div>
            <p class="eyebrow">Stop ${String(stop.order).padStart(2, "0")}</p>
            <h3>${stop.name || "未命名地点"}</h3>
            <p>${stop.formattedAddress || "暂无格式化地址，已保留照片 GPS 坐标。"}</p>
            <div class="poi-list">${pois || "<span>暂无附近 POI</span>"}</div>
            <p>${stop.caption || ""}</p>
            <div class="source-list"><span>${stop.dataSource || "EXIF GPS"}</span><span>${stop.note || "坐标可能存在偏移"}</span></div>
            <div class="stop-photos">${photos}</div>
          </div>
        </article>
      `;
    })
    .join("");
};

const renderPhotoWall = (photos = []) => {
  const target = document.querySelector("#photoWall");
  if (!photos.length) {
    target.innerHTML = '<div class="empty">暂无照片。</div>';
    return;
  }
  target.innerHTML = photos.map((photo) => `<img src="${photo.src}" alt="${photo.filename}" loading="lazy" />`).join("");
};

const renderAlbum = (album) => {
  document.title = "StoryAlbum Geo｜基于照片地址的旅行回忆相册";
  setImage("#coverImage", album.cover, "暂无封面照片");
  renderStats(album.stats);
  renderMapComparison(album);
  renderStops(album.stops);
  renderPhotoWall(album.photos);
};

if (window.STORYALBUM_GEO_DATA) {
  renderAlbum(window.STORYALBUM_GEO_DATA);
} else {
  fetch(DATA_URL)
    .then((response) => {
      if (!response.ok) throw new Error(`Failed to load ${DATA_URL}`);
      return response.json();
    })
    .then(renderAlbum)
    .catch((error) => {
      document.querySelector("main").insertAdjacentHTML("afterbegin", `<section class="section"><div class="empty">${error.message}</div></section>`);
    });
}

