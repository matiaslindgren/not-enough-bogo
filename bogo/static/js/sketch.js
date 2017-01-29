
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
    const wrapper = this;

    const s = function(p) {

      let sketchWidth = wrapper.width;
      let sketchHeight = wrapper.height;

      const getColumnWidth = function() {
        return sketchWidth/wrapper.columns/wrapper.spacing;
      }

      const getColumnHeightStep = function() {
        return wrapper.spacing*(sketchHeight - wrapper.yPadding)/wrapper.columns;
      }

      let columnWidth = getColumnWidth();
      let columnHeightStep = getColumnHeightStep();

      let sequence = wrapper.sequence;

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
          const x = wrapper.spacing*i*columnWidth;
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
        canvas.parent(wrapper.containerId);
        shuffle();
        p.loop();
      }

      p.draw = function() {
        p.background(255, 40);

        if (wrapper.shufflin) {
          shuffle();
        }
        if (wrapper.sorted) {
          p.noLoop();
          p.clear(); // Background is opaque
          sort();
        }

        drawSequence();
      }

      p.windowResized = function() {
        const canvasParent = $(canvas.parent());
        resizeSketch(canvasParent.width(), canvasParent.height());

        p.resizeCanvas(sketchWidth, sketchHeight);

        if (!wrapper.shufflin)
          p.draw();
      }
    }
    return s;
  }
};


