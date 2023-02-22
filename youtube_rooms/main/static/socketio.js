$(window).bind("pageshow", function (event) {
  if (event.originalEvent.persisted) {
    socket.disconnect();
    socket = null;
    initiateConnection();
  }
});
$(document).ready(initiateConnection());

function initiateConnection() {

  room_name = decodeURI(window.location.pathname.split("/").at(-1));

  var socket = io(
    `${window.location.host}?room_name=${room_name}&websocket_csrf=${websocket_csrf}`,
    {
      rememberTransport: false,
      transports: ["websocket"],
    }
  );
  window.socket = socket;

  socket.on("my_response", function (msg) {
    createMessageDiv("ROOM", msg.data);
  });

  socket.on("start_video", function (msg) {
    youtubeVideo.removeIframeAndAddEmptyDiv();
    let video = new youtubeVideo(msg.current_video, msg.time_stamp, socket);
    window.video = video;
    if (window.isYoutubeApiLoaded) {
      video.loadVideo();
    } else {
      //Youtube api calls onYouTubeIframeAPIReady by default once it loads.
      youtubeVideo.loadYoutubeApi();
    }
  });

  socket.on("sync_video", function (msg) {
    video.goTo(msg.time_stamp);
  });

  $("form#emit").submit(function (event) {
    socket.emit("my_event", { room_name: room_name });
    return false;
  });

  $("form#form").submit(function (event) {
    socket.emit("submit_video_event", {
      data: $("#broadcast_data").val(),
      room_name: room_name,
    });
    return false;
  });

  socket.on("chat_message", function (msg) {
    createMessageDiv(msg.username, msg.chat_message, msg.color);
  });

  socket.on("connect", function () {
    socket.emit("set_room_name_event", {
      data: room_name,
      room_name: room_name,
    });

    return false;
  });
}
///////////////////////////////////////////////////////////////////////////
///////////////////////Youtube API////////////////////////////////////////
/////////////////////////////////////////////////////////////////////////
class youtubeVideo {
  constructor(videoId, videoTimeStamp, socket) {
    this.socket = socket;
    this.player = null;
    this.videoId = videoId;
    window.onYouTubeIframeAPIReady = this.loadVideo.bind(this);
    this.seek = Math.round(parseInt(videoTimeStamp)) || 0;
    this.previousAndCurrentState = [-1, -1];
  }
  loadVideo() {
    this.player = new YT.Player("player", {
      videoId: this.videoId,
      playerVars: {
        origin: "https://localhost:5000",
        playsinline: 1,
        autoplay: 1,
      },
      events: {
        onReady: this.onPlayerReady.bind(this),
        onStateChange: this.onPlayerStateChange.bind(this),
      },
    });
  }
  onPlayerReady(event) {
    event.target.mute();
    event.target.playVideo();
    this.socket.emit("sync_data", { data: "", room_name: room_name });
  }
  onPlayerStateChange(event) {
    event.target.unMute();
    this.previousAndCurrentState.shift();
    this.previousAndCurrentState.push(event.data);

    if (
      //if the user pauses then resumes the video, sync the video
      (this.previousAndCurrentState[0] == 2 &&
        this.previousAndCurrentState[1] == 1) ||
      (this.previousAndCurrentState[0] == -1 &&
        this.previousAndCurrentState[1] == 1)
    ) {
      this.socket.emit("sync_data", { data: "", room_name: room_name });
    }
  }
  goTo(time) {
    this.player.seekTo(Math.round(parseInt(time)));
  }
  startVideo() {
    this.player.playVideo();
  }

  static loadYoutubeApi() {
    if (!window.isYoutubeApiLoaded) {
      $.getScript("https://www.youtube.com/iframe_api", function () {
        window.isYoutubeApiLoaded = true;
      });
    }
  }
  static removeIframeAndAddEmptyDiv() {
    $("#player").remove();
    $(".player__div").prepend(
      jQuery("<div>", {
        id: "player",
      })
    );
  }
}

///////////////////////////////////////////////////////////////////////////
///////////////////////chat functions/////////////////////////////////////
/////////////////////////////////////////////////////////////////////////
$(".chat__send__message__input").keydown(function (e) {
  if (e.keyCode === 13) {
    //myUsername is sent by the server through the jinja template room.jinja2
    createMessageDiv(myUsername, $(".chat__send__message__input").val(), color);
    socket.emit("chat_message", {
      chat_message: $(".chat__send__message__input").val(),
      room_name: room_name,
    });
    $(".chat__send__message__input").val("")
  }
});

$(".send__message__svg").click(function (e) {
  //myUsername is sent by the server through the jinja template room.jinja2
  createMessageDiv(myUsername, $(".chat__send__message__input").val());
  socket.emit("chat_message", {
    chat_message: $(".chat__send__message__input").val(""),
    room_name: room_name,
  });
  $(".chat__send__message__input").val()=""
});

function createMessageDiv(username, message, color = "white") {
  //create a div containing 3 spans for the message data
  messageDiv = document.createElement("div");
  jQuery("<span>", {
    class: "message__timestamp",
    text: getTimestamp() + " ",
  }).appendTo(messageDiv);
  jQuery("<span>", {
    class: "message__username",
    text: String(username) + " : ",
  })
    .css("color", color)
    .appendTo(messageDiv);

  jQuery("<span>", {
    class: "message__text",
    text: String(message),
  }).appendTo(messageDiv);
  
  $(messageDiv).addClass("chat__message__unit");
  $(messageDiv).appendTo($(".chat__messages"));
  chatDiv = document.getElementsByClassName("chat__messages")[0];
  chatDiv.scrollTop = chatDiv.scrollHeight;
}

function getTimestamp() {
  let currDate = new Date();
  let colon = ":";
  minutes = currDate.getMinutes();
  if (minutes < 10) {
    colon = ":0";
  }
  let hoursMin = currDate.getHours() + colon + currDate.getMinutes();
  return String(hoursMin);
}
function rem() {
  var html = document.getElementsByTagName("html")[0];

  return parseInt(window.getComputedStyle(html)["fontSize"]);
}
