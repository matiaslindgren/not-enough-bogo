
const SKETCH_CONFIG = {
  spacing:      0.05,
  yPadding:     0,
  backgroundAlpha: 30
}


class AnimationWrapper {
  constructor(settings) {
    this.containerId     = settings.containerId;
    this.columns         = settings.columns;
    this.sorted          = settings.sorted;

    this.spacing         = 1.0 + ((settings.spacing !== undefined) ? settings.spacing : SKETCH_CONFIG.spacing);
    this.yPadding        = (settings.yPadding !== undefined) ? settings.yPadding : SKETCH_CONFIG.yPadding;
    this.backgroundAlpha = (settings.backgroundAlpha !== undefined) ? settings.backgroundAlpha : SKETCH_CONFIG.backgroundAlpha;

    this.shufflin        = !this.sorted;
    this.sequence        = _.range(1, this.columns+1);
  }

  // Switches to alter the state of the returned p5 instance

  /** Stop shuffling columns. */
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

      // Optimizations
      let sketchWidth;
      let sketchHeight;
      let columnWidth;
      let columnHeightStep;

      const refreshSizes = function() {
        const container = $('#' + wrapper.containerId);

        sketchWidth      = container.width();
        sketchHeight     = container.height();
        columnWidth      = (wrapper.spacing/wrapper.columns) + sketchWidth/wrapper.columns/wrapper.spacing;
        columnHeightStep = (sketchHeight - wrapper.yPadding)/wrapper.columns;
      }

      let sequence = wrapper.sequence;

      const shuffle = function() {
        sequence = _.shuffle(sequence);
      }

      const sort = function() {
        sequence = _.sortBy(sequence);
      }

      const drawSequence = function() {
        p.noStroke();
        p.fill(150);

        _.each(sequence, (num, i) => {
          const x = wrapper.spacing*i*columnWidth;
          const height = num*columnHeightStep;
          const y = sketchHeight - height;
          p.rect(x, y, columnWidth, height);
        });
      }

      p.setup = function() {
        const canvas = p.createCanvas();
        canvas.parent(wrapper.containerId);

        refreshSizes();
        p.resizeCanvas(sketchWidth, sketchHeight);

        shuffle();
        p.loop();
      }

      p.draw = function() {
        p.background(255, wrapper.backgroundAlpha);

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
        refreshSizes();
        p.resizeCanvas(sketchWidth, sketchHeight);
        if (wrapper.sorted)
          p.draw();
      }
    }
    return s;
  }
};


