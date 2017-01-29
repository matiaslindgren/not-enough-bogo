const backendData = JSON.parse($("#backend-render-context").html());
const columns = backendData.columnCount ? parseInt(backendData.columnCount) : 10000;

const animationSettings = {
  containerId:     "dummy-sort-container",
  columns:         columns,
  sorted:          false,
  yPadding:        0,
  spacing:         1,
  backgroundAlpha: 60
}
const animationWrapper = new AnimationWrapper(animationSettings);
const p5app = new p5(animationWrapper.p5sketch());
