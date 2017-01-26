

class SequenceSketch {
  constructor(height, width, spacing, yPadding, columns, containerId) {
    this.height = height;
    this.width = width;
    this.spacing = spacing;
    this.yPadding = yPadding;
    this.columns = columns;
    this.containerId = containerId;
    this.sequence = _.range(1, columns+1);
    this.shufflin = true;
  }

  stopShuffling() {
    // pull carpet from under the sketch instance returned by p5sketch
    this.shufflin = false;
  }

  // Capture the state of this sketch and 'render' it as an p5 instance.
  p5sketch() {
    const sketch = this;

    const s = function(p) {

      let sketchWidth = sketch.width;
      let sketchHeight = sketch.height;

      let columnWidth = sketch.width/sketch.columns/sketch.spacing;
      let columnHeightStep = sketch.spacing*(sketch.height - yPadding)/sketch.columns;

      let sequence = sketch.sequence;

      let canvas = null;

      const shuffle = function() {
        sequence = _.shuffle(sequence);
      }

      const sort = function() {
        sequence = _.sortBy(sequence);
      }

      const drawSequence = function() {
        p.noStroke();
        p.fill(150);

        for (let i = 0; i < sequence.length; i++) {
          const x = sketch.spacing*i*columnWidth;
          const height = sequence[i]*columnHeightStep;
          const y = sketchHeight - height;
          p.rect(x, y, columnWidth, height);
        }
      }

      const resizeSketch = function(newWidth, newHeight) {
        sketchHeight = newHeight;
        sketchWidth = newWidth;
        columnWidth = sketchWidth/sketch.columns/sketch.spacing;
        columnHeightStep = sketch.spacing*(sketchHeight - yPadding)/sketch.columns;
      }

      p.setup = function() {
        canvas = p.createCanvas(sketchWidth, sketchHeight);
        canvas.parent(sketch.containerId);
        p.loop();
      }

      p.draw = function() {
        p.background(255, 40);

        if (sketch.shufflin) {
          shuffle();
        }
        else {
          p.clear(); // Background is opaque
          sort();
          p.noLoop();
        }

        drawSequence();
      }

      p.windowResized = function() {
        const canvasParent = $(canvas.parent());
        resizeSketch(canvasParent.width(), canvasParent.height());

        p.resizeCanvas(sketchWidth, sketchHeight);

        if (!sketch.shufflin)
          p.draw();
      }
    }
    return s;
  }
};


const canvasContainerId = 'sketch-container';
const canvasWidth = $("#sketch-container").width();
const canvasHeight = $("#sketch-container").height();
const spacing = 1.1;
const yPadding = 60;
const columns = 20;

const activeSketch = new SequenceSketch(canvasHeight, canvasWidth, spacing, yPadding, columns, canvasContainerId);

const p5app = new p5(activeSketch.p5sketch());


