const repoNameEl = document.getElementById("repo-name");
const versionNameEl = document.getElementById("version-name");
const publishedAtEl = document.getElementById("published-at");
const releaseNotesEl = document.getElementById("release-notes");
const assetListEl = document.getElementById("asset-list");
const downloadLinkEl = document.getElementById("download-link");
const releaseLinkEl = document.getElementById("release-link");
const statusMessageEl = document.getElementById("status-message");
const releaseAssetPrefix = window.releaseAssetPrefix || "";

function detectRepository() {
  const host = window.location.hostname.toLowerCase();
  const pathSegments = window.location.pathname.split("/").filter(Boolean);

  let owner = "";
  let repo = "";

  if (host.endsWith(".github.io")) {
    owner = host.split(".github.io")[0];
    repo = pathSegments[0] || "";
  }

  return { owner, repo };
}

function setStatus(message) {
  statusMessageEl.textContent = message;
}

function formatDate(dateString) {
  if (!dateString) {
    return "未知";
  }

  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return dateString;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function renderAssets(assets) {
  assetListEl.innerHTML = "";

  if (!assets.length) {
    const item = document.createElement("li");
    item.textContent = "这个版本没有可下载附件。";
    assetListEl.appendChild(item);
    return;
  }

  assets.forEach((asset) => {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = asset.browser_download_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = `${asset.name} (${(asset.size / 1024 / 1024).toFixed(2)} MB)`;
    item.appendChild(link);
    assetListEl.appendChild(item);
  });
}

function setPrimaryDownload(asset) {
  if (!asset) {
    downloadLinkEl.textContent = "暂无可下载版本";
    downloadLinkEl.setAttribute("aria-disabled", "true");
    downloadLinkEl.href = "#";
    return;
  }

  downloadLinkEl.textContent = `下载 ${asset.name}`;
  downloadLinkEl.href = asset.browser_download_url;
  downloadLinkEl.removeAttribute("aria-disabled");
}

function isPreferredAsset(asset) {
  const name = asset.name.toLowerCase();
  if (releaseAssetPrefix) {
    return name.startsWith(releaseAssetPrefix.toLowerCase()) && name.endsWith(".exe");
  }
  return name.endsWith(".exe");
}

function pickRelease(releases) {
  for (const release of releases) {
    const assets = Array.isArray(release.assets) ? release.assets : [];
    const matchingAssets = assets.filter(isPreferredAsset);
    if (matchingAssets.length) {
      return { release, assets: matchingAssets };
    }
  }
  return null;
}

async function loadLatestRelease() {
  const { owner, repo } = detectRepository();

  if (!owner || !repo) {
    repoNameEl.textContent = "无法自动识别仓库";
    versionNameEl.textContent = "请使用 GitHub Pages 项目页";
    publishedAtEl.textContent = "-";
    releaseNotesEl.textContent =
      "当前页面没法自动识别 GitHub 用户名和仓库名。建议使用默认的 GitHub Pages 地址，例如 https://用户名.github.io/仓库名/";
    setPrimaryDownload(null);
    renderAssets([]);
    setStatus("仓库信息识别失败。");
    return;
  }

  const repoLabel = `${owner}/${repo}`;
  const releaseUrl = `https://github.com/${repoLabel}/releases`;
  const apiUrl = `https://api.github.com/repos/${repoLabel}/releases?per_page=30`;

  repoNameEl.textContent = repoLabel;
  releaseLinkEl.href = releaseUrl;

  try {
    const response = await fetch(apiUrl, {
      headers: {
        Accept: "application/vnd.github+json",
      },
    });

    if (!response.ok) {
      throw new Error(`GitHub API 返回 ${response.status}`);
    }

    const releases = await response.json();
    const selected = pickRelease(Array.isArray(releases) ? releases : []);

    if (!selected) {
      throw new Error("没有找到对应的 exe Release");
    }

    const { release, assets } = selected;
    const preferredAsset = assets[0];

    versionNameEl.textContent = release.name || release.tag_name || "未命名版本";
    publishedAtEl.textContent = formatDate(release.published_at || release.created_at);
    releaseNotesEl.textContent = release.body || "这个版本没有填写说明。";
    renderAssets(assets);
    setPrimaryDownload(preferredAsset);
    releaseLinkEl.href = release.html_url || releaseUrl;
    setStatus("已加载最新 Release。");
  } catch (error) {
    versionNameEl.textContent = "读取失败";
    publishedAtEl.textContent = "-";
    releaseNotesEl.textContent =
      "还没有找到可用的 Release。请先等待 GitHub Actions 发布完成，或检查仓库是否已经创建过公开 Release。";
    renderAssets([]);
    setPrimaryDownload(null);
    setStatus(`读取失败：${error.message}`);
  }
}

loadLatestRelease();
