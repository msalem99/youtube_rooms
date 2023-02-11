// 2. This code loads the IFrame Player API code asynchronously.

function initiateYoutubePlayer(videoId) {
  var tag = document.createElement("script");
  tag.src = "https://www.youtube.com/iframe_api";
  var firstScriptTag = document.getElementsByTagName("script")[0];
  firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

  // 3. This function creates an <iframe> (and YouTube player)
  //    after the API code downloads.
  var player;
  window.onYouTubeIframeAPIReady = loadYoutube;
  function loadYoutube() {
    console.log("test");
    player = new YT.Player("player", {
      height: "390",
      width: "640",
      videoId: videoId,
      playerVars: {
        origin: "https://localhost:5000",
        playsinline: 1,
      },
      events: {
        onReady: onPlayerReady,
        onStateChange: onPlayerStateChange,
      },
    });
  }
}
// 4. The API will call this function when the video player is ready.
function onPlayerReady(event) {
  event.target.playVideo();
}

// 5. The API calls this function when the player's state changes.
//    The function indicates that when playing a video (state=1),
//    the player should play for six seconds and then stop.
// var done = false;
// function onPlayerStateChange(event) {
//   console.log("change");
// }
// function stopVideo() {
//   player.stopVideo();
// }
