
const canvasWidth = 700;
const canvasHeight = 400;
const canvasContainerId = 'canvas-container';

function setup() {
  createCanvas(canvasWidth, canvasHeight);
  canvas.parent(canvasContainerId);
  background(255, 50);
}

function draw() {
  fill(150);
  rect(100, 100, 50, 50);
}
