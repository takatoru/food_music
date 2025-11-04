let foodData = {};

// ===== JSON読み込み =====
async function loadData() {
  try {
    const res = await fetch("data.json", { cache: "no-store" });
    foodData = await res.json();
    populateFoodList();
  } catch (err) {
    console.error("❌ JSONの読み込みに失敗しました:", err);
    alert("データの読み込みに失敗しました。data.json の場所と内容を確認してください。");
  }
}

// ===== 料理一覧を生成 =====
function populateFoodList() {
  const foodSelect = document.getElementById("food");
  foodSelect.innerHTML = '<option value="">-- 選択してください --</option>';

  Object.keys(foodData).forEach(foodName => {
    const opt = document.createElement("option");
    opt.value = foodName;
    opt.textContent = foodName;
    foodSelect.appendChild(opt);
  });

  foodSelect.addEventListener("change", handleFoodChange);
}

// ===== 味覚選択欄の表示制御（allow_choice=TRUEのときだけ） =====
function handleFoodChange() {
  const selectedFood = document.getElementById("food").value;
  const tasteSection = document.getElementById("taste-section");
  const tasteSelect = document.getElementById("taste");

  tasteSelect.innerHTML = '<option value="">-- 選択してください --</option>';
  tasteSection.style.display = "none";

  if (!selectedFood || !foodData[selectedFood]) return;

  const options = foodData[selectedFood].options || [];
  if (options.length > 0) {
    tasteSection.style.display = "block";
    options.forEach(taste => {
      const opt = document.createElement("option");
      opt.value = taste;
      opt.textContent = translateTaste(taste);
      tasteSelect.appendChild(opt);
    });
  }
}

// ===== 味覚コード→日本語表記 =====
function translateTaste(taste) {
  const map = { sweet: "甘味", sour: "酸味", bitter: "苦味", salty: "塩味", spicy: "辛味", umami: "旨味" };
  return map[taste] || taste;
}

// ===== moodに対応する曲配列を取得（data.jsonの構造に合わせる） =====
function getTracksFor(food, mood) {
  const block = foodData?.[food]?.music;
  if (!block) return [];
  const tracks = block[mood] || [];
  // NaNや空文字の混入を念のため除外
  return tracks.filter(t => t && t.uri && String(t.uri).trim() !== "");
}

// ===== rank優先 → 重み付きランダムで1曲選ぶ =====
function pickOneTrack(tracks) {
  if (!tracks || tracks.length === 0) return null;

  // rankがある曲を優先（rank数値が小さいほど優先）
  const withRank = tracks.filter(t => Number.isFinite(t.rank));
  if (withRank.length > 0) {
    withRank.sort((a, b) => a.rank - b.rank);
    return withRank[0];
  }

  // weight（なければ1.0）で重み付きランダム
  const weights = tracks.map(t => Number.isFinite(t.weight) ? t.weight : 1.0);
  const total = weights.reduce((s, w) => s + w, 0);
  let r = Math.random() * total;
  for (let i = 0; i < tracks.length; i++) {
    if ((r -= weights[i]) <= 0) return tracks[i];
  }
  return tracks[tracks.length - 1]; // フォールバック
}

// ===== 再生処理（ローカル音源は<audio>、URLは新規タブ） =====
function playTrack(track) {
  const audio = document.getElementById("audioPlayer");
  const uri = String(track.uri);

  const isLocalAudio =
    uri.startsWith("audio/") ||
    uri.endsWith(".mp3") || uri.endsWith(".m4a") || uri.endsWith(".wav") || uri.endsWith(".ogg");

  if (isLocalAudio) {
    audio.src = uri;
    audio.play().catch(e => console.warn("再生エラー:", e));
  } else {
    // YouTube/Spotify等はブラウザの制約上 <audio> 直再生不可が多いので新規タブへ
    window.open(uri, "_blank");
  }
}

// ===== クリック：曲を選んで再生 =====
document.getElementById("playBtn").addEventListener("click", () => {
  const food = document.getElementById("food").value;
  const mood = document.getElementById("mood").value;
  const tasteUIShown = document.getElementById("taste-section").style.display !== "none";
  const taste = document.getElementById("taste").value;

  if (!food || !mood) {
    alert("料理と気分を選択してください。");
    return;
    }

  if (tasteUIShown && !taste) {
    alert("味覚も選択してください。");
    return;
  }

  // 現状のdata.jsonは「食品のdefault_tasteに紐づく曲」を保持。
  // tasteドロップダウンはUI表示のみ（option_taste切替は将来拡張）。
  const tracks = getTracksFor(food, mood);
  if (tracks.length === 0) {
    alert("この組み合わせの曲が未登録です。ExcelシートBに曲を追加し、JSONを更新してください。");
    return;
  }

  const track = pickOneTrack(tracks);
  if (!track) {
    alert("曲の選択に失敗しました。");
    return;
  }

  playTrack(track);

  // 画面通知（デバッグ用）
  const title = track.title || "(無題)";
  const where = track.uri || "";
  alert(`♪ 再生候補\n料理: ${food}\n気分: ${displayMood(mood)}\n曲: ${title}\nURI: ${where}`);
});

// 気分の表示用
function displayMood(mood) {
  const map = { relaxation: "リラックス", excitement: "元気", focus: "集中", calm: "落ち着き" };
  return map[mood] || mood;
}

// ===== 起動 =====
document.addEventListener("DOMContentLoaded", loadData);
