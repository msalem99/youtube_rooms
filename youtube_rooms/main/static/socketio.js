$(window).bind("pageshow", function (event) {
  if (event.originalEvent.persisted) {
    initiateConnection();
  }
});
$(document).ready(initiateConnection());

function initiateConnection() {
  room_name = decodeURI(window.location.pathname.split("/").at(-1));
  console.log(window.location.host);
  var socket = io("http://192.168.1.114:5000", {
    rememberTransport: false,
    transports: ["websocket"],
  });
  window.socket = socket;

  socket.on("my_response", function (msg) {
    $("#log").append("<p>Received: " + msg.data + "</p>");
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

  $("form#broadcast").submit(function (event) {
    socket.emit("submit_video_event", {
      data: $("#broadcast_data").val(),
      room_name: room_name,
    });
    return false;
  });

  socket.on("chat_message", function (msg) {
    createMessageDiv(msg.username, msg.chat_message);
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
    this.videoId = videoId || videoData;
    window.onYouTubeIframeAPIReady = this.loadVideo.bind(this);
    this.seek = Math.round(parseInt(videoTimeStamp)) || 0;
    this.previousAndCurrentState = [-1, -1];
  }
  loadVideo() {
    this.player = new YT.Player("player", {
      height: "600",
      width: "800",
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
    this.socket.emit("sync_data", { data: "sync me", room_name: room_name });
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
      this.socket.emit("sync_data", { data: "sync me", room_name: room_name });
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
    $(".left__side").prepend(
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
    createMessageDiv(myUsername, $(".chat__send__message__input").val());
    socket.emit("chat_message", {
      chat_message: $(".chat__send__message__input").val(),
      room_name: room_name,
    });
  }
});

$(".send__message__svg").click(function (e) {
  //myUsername is sent by the server through the jinja template room.jinja2
  createMessageDiv(myUsername, $(".chat__send__message__input").val());
  socket.emit("chat_message", {
    chat_message: $(".chat__send__message__input").val(),
    room_name: room_name,
  });
});

function createMessageDiv(username, message) {
  //create a div containing 3 spans for the timestamp,username and message
  messageDiv = document.createElement("div");
  jQuery("<span>", {
    class: "message__timestamp",
    text: getTimestamp(),
  }).appendTo(messageDiv);
  jQuery("<span>", {
    class: "message__username",
    text: String(username),
  }).appendTo(messageDiv);
  jQuery("<span>", {
    class: "message__text",
    text: String(message),
  }).appendTo(messageDiv);
  console.log(messageDiv);
  $(messageDiv).addClass("chat__message__unit");
  $(messageDiv).appendTo($(".chat__messages"));
}

function getTimestamp() {
  let currDate = new Date();
  let hoursMin = currDate.getHours() + ":" + currDate.getMinutes();
  return String(hoursMin);
}
