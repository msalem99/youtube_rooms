$(window).bind("pageshow", function (event) {
  if (event.originalEvent.persisted) {
    initiateConnection();
  }
});
$(document).ready(initiateConnection());

function initiateConnection() {
  room_name = decodeURI(window.location.pathname.split("/").at(-1));

  console.log(room_name);
  var socket = io(window.location.host, {
    rememberTransport: false,
    transports: ["websocket"],
  });

  socket.on("my_response", function (msg) {
    $("#log").append("<p>Received: " + msg.data + "</p>");
  });
  socket.on("start_video", function (msg) {
    initiateYoutubePlayer(msg.data);
    console.log(msg.data);
  });

  $("form#emit").submit(function (event) {
    socket.emit("my_event", { data: "dataa" });

    return false;
  });

  $("form#broadcast").submit(function (event) {
    socket.emit("submit_video_event", { data: $("#broadcast_data").val() });
    return false;
  });

  socket.on("connect", function () {
    socket.emit("my_event", { data: "I'm connected!" });
    socket.emit("set_room_name_event", { data: room_name });

    return false;
  });
}
