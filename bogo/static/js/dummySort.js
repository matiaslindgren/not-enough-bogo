const backendData = JSON.parse($("#backend-render-context").html());
const columns = backendData.columnCount ? parseInt(backendData.columnCount) : 10000;

const animationSettings = {
  containerId:     "dummy-sort-container",
  columns:         columns,
  sorted:          false,
  yPadding:        0,
  spacing:         0.05,
  backgroundAlpha: 50
}
const animationWrapper = new AnimationWrapper(animationSettings);
const p5app = new p5(animationWrapper.p5sketch());

function toggleFullScreen() {
  var canvasElement = $("canvas")[0];

  if (!document.mozFullScreen && !document.webkitFullScreen) {
    if (canvasElement.mozRequestFullScreen) {
      canvasElement.mozRequestFullScreen();
    } else {
      canvasElement.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);
    }
    // hacky hackerpants strikes again, couldn't get the fullscreenchange-events to work
    setTimeout(_ => {
      $("canvas").width($(window).width());
      $("canvas").height($(window).height());
    }, 100);
  } else {
    if (document.mozCancelFullScreen) {
      document.mozCancelFullScreen();
    } else {
      document.webkitCancelFullScreen();
    }
  }

  document.addEventListener("keydown", e => {
    if (e.keyCode == 13) {
      toggleFullScreen();
    }
  }, false);
}


