

class SequenceSketch {
  constructor(settings) {
    this.containerId = settings.containerId;
    this.height =      settings.canvasHeight;
    this.width =       settings.canvasWidth;
    this.spacing =     settings.spacing;
    this.columns =     settings.columns;
    this.yPadding =    settings.yPadding;
    this.shufflin =    settings.shufflin;

    this.sequence = _.range(1, this.columns+1);
  }

  stopShuffling() {
    // pull carpet from under the sketch instance returned by p5sketch
    this.shufflin = false;
  }

  // Capture the state of this sketch and 'render' it as an p5 instance.
  p5sketch() {
    const sketch = this;

    const s = function(p) {

      const getColumnWidth = function() {
        return sketch.width/sketch.columns/sketch.spacing;
      }

      const getColumnHeightStep = function() {
        return sketch.spacing*(sketch.height - sketch.yPadding)/sketch.columns;
      }


      let sketchWidth = sketch.width;
      let sketchHeight = sketch.height;

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


