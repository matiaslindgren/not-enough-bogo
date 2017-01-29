
const SKETCH_CONFIG = {
  spacing:      1.1,
  yPadding:     60,
}


class AnimationWrapper {
  constructor(settings) {
    this.containerId = settings.containerId;
    this.columns     = settings.columns;
    this.sorted      = settings.sorted;

    this.shufflin    = !this.sorted;

    this.spacing     = SKETCH_CONFIG.spacing;
    this.yPadding    = SKETCH_CONFIG.yPadding;

    this.sequence    = _.range(1, this.columns+1);
  }

  // Switches to alter the state of the returned p5 instance

  /** Stop shuffling columns but don't stop looping. */
  stopShuffling() {
    this.shufflin = false;
  }

  /** Resume shuffling. */
  startShuffling() {
    this.shufflin = true;
  }

  /** Clear canvas, sort columns and stop looping. */
  setSorted() {
    this.sorted = true;
  }

  /** Return a p5 instance with access to the state of AnimationWrapper. */
  p5sketch() {
    const sketch = this;

    const s = function(p) {

      let sketchWidth = sketch.width;
      let sketchHeight = sketch.height;

      const getColumnWidth = function() {
        return sketchWidth/sketch.columns/sketch.spacing;
      }

      const getColumnHeightStep = function() {
        return sketch.spacing*(sketchHeight - sketch.yPadding)/sketch.columns;
      }

      let columnWidth = getColumnWidth();
      let columnHeightStep = getColumnHeightStep();

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
        columnWidth = getColumnWidth();
        columnHeightStep = getColumnHeightStep();
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


