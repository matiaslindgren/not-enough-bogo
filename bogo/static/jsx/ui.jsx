import React from 'react';
import ReactDOM from 'react-dom';

/**
 * React component. The top-level component containing all elements on the page with non-static state.
 * @extends React.Component
 */
class Bogo extends React.Component {
  /**
   * Create Bogo with state variables set to "Loading...".
   * @param {Object} props
   * @param {string} props.bogoId - Id of this Bogo in the backend
   * @param {string} props.activeStateUrl - JSON API URL to be polled for changes in state.
   * @param {string} props.updateApiUrl - URL for full statistics, should be considered slow.
   * @param {string} props.animationSettings - Parameters for the SequenceSketch object which wraps the p5js instance responsible of drawing the animation.
   * @param {string} props.activeName - Name of the current state.
   * @param {string} props.previousUrl - URL for pager previous button.
   * @param {string} props.nextUrl - URL for pager next button.
   */
  constructor(props) {
    super(props);

    let state;

    if (props.endDate) {
      state = {
        stateName: "Sorted",
        endDate: props.endDate,
        currentSpeed: "-"
      }
    }
    else {
      state = {
        stateName: this.generateActiveName(),
        endDate: "Maybe some day",
        currentSpeed: "Loading..."
      }
    }
    this.state = Object.assign(
      state,
      { previousUrl: this.props.previousUrl,
        nextUrl: this.props.nextUrl }
    );
  }

  /** Return a random string prefixed by 'Bogosorting '. The random string may or may not be funny.  */
  generateActiveName() {
    const states = [
      "with great enthusiasm",
      "vigorously",
      "with seemingly unlimited passion",
      "rather impetuously",
      "in an unreasoned manner",
      "like a furious Jerboa",
      "with passion",
      "ironically fast",
      "while occasionally sipping cheap red wine",
      "furiously, angrily even",
      "with white shores and green fields in mind",
      "and thinking of tomorrow",
      "platonically, whatever that means in this context",
      "with utmost haste",
      "whilst questioning the meaning of all this",
      "with a tad of melancholy"
    ];
    return "Bogosorting " + states[Math.floor(Math.random()*states.length)];
  }

  /**
   * If the state is not "Sorted", set timer for calling refreshState and draw animation with shuffling.
   * Else, do not set a timer and draw one frame of a sorted sequence.
   */
  componentDidMount() {
    const isSorted = this.state.stateName === "Sorted";

    if (!isSorted) {
      // TODO the lambda is redundant? test
      this.timerID = setInterval(_ => this.refreshState(), 1000);
    }

    const animationSettings = Object.assign(
      this.props.animationSettings,
      { shufflin: !isSorted,
        columns:  this.props.sequenceLength }
    );
    // animate
    this.animation = new SequenceSketch(animationSettings);
    this.p5app = new p5(this.animation.p5sketch());

    console.warn(this.animation);
    console.warn(this.p5app);
  }

  /** The sequence is sorted, stop refresh timer and animation. */
  componentWillUnmount() {
    if (this.timerID)
      clearInterval(this.timerID);
    if (this.animation)
      this.animation.stopShuffling();
  }

  /**
   * Make a GET-request to this.props.activeStateUrl and update own state.
   * If the state changes to sorted, stop polling this.props.updateApiUrl.
   */
  refreshState() {
    const activeStateUrl = this.props.activeStateUrl;

    // Retrieve current state
    $.getJSON(activeStateUrl, data => {

      // If the returned state id is different from this Bogo,
      // the sequence has been sorted in the backend.
      if (data.activeId !== this.props.bogoId) {
        // Retrieve full statistics for this Bogo and stop everything.
        $.getJSON(this.props.updateApiUrl, fullData => {
          this.componentWillUnmount();
          this.setState({
            stateName: "Sorted",
            endDate: fullData.endDate,
            currentSpeed: "-",
            previousUrl: fullData.previousUrl,
            nextUrl: fullData.nextUrl
          });
        });
      }
      else {
        this.setState({
          currentSpeed: Math.round(data.currentSpeed) + " shuffles per second"
        });
      }

    });
  }

  /** Render this component with a Table and Pager. */
  render() {
    return (
      <div>
        <Table stateName=     {this.state.stateName}
               startDate=     {this.props.startDate}
               endDate=       {this.state.endDate}
               sequenceLength={this.props.sequenceLength}
               currentSpeed=  {this.state.currentSpeed} />
        <Pager previousUrl=   {this.state.previousUrl}
               nextUrl=       {this.state.nextUrl}/>
      </div>
    );
  }
}


/**
 * React component. A Table containing Row-components.
 * @param {Object} props
 * @param {string} props.stateName
 * @param {string} props.startDate
 * @param {string} props.endDate
 * @param {string} props.sequenceLength
 * @param {string} props.currentSpeed
 */
function Table(props) {
  const sortProbability = 0; // tODO
  return (
    <div>
      <table className="table table-bordered table-condensed">
        <tbody>
          <Row label="State"               value={props.stateName} />
          <Row label="Sorting started at"  value={props.startDate} />
          <Row label="Sorting finished at" value={props.endDate} />
          <Row label="Sequence length"     value={props.sequenceLength} />
          <Row label="Current speed"       value={props.currentSpeed} />
        </tbody>
      </table>
    </div>
  );
}


/**
 * React component. One table row with a label and value.
 * @param {Object} props
 * @param {string} props.label
 * @param {string} props.value
 */
function Row(props) {
  return (
    <tr>
      <td className="col-xs-4">{props.label}</td>
      <td className="col-xs-8">{props.value}</td>
    </tr>
  );
}


/**
 * React component. Pager with two buttons: older and newer.
 * @param {Object} props
 * @param {string} props.previousUrl - Value for the href-attribute in the button labeled 'Older'. If not given, a button labeled 'Older' will not be generated.
 * @param {string} props.nextUrl - Value for the href-attribute in the button labeled 'Newer'. If not given, a button labeled 'Newer' will not be generated.
 */
function Pager(props) {
  return (
    <div className="container">
      <nav aria-label="...">
        <ul className="pager">
          {(props.previousUrl && props.previousUrl.length > 0) &&
            <li className="previous">
              <a href={props.previousUrl}><span aria-hidden="true">&larr;</span> Older</a>
            </li>}
          {(props.nextUrl && props.nextUrl.length > 0) &&
            <li className="next">
              <a href={props.nextUrl}>Newer <span aria-hidden="true">&rarr;</span></a>
            </li>}
        </ul>
      </nav>
    </div>
  );
}


/** Call ReactDOM.render and render all components. */
function uiMain() {
  // Get backend json api url for statistics
  const staticData = JSON.parse($("#bogo-data-api").html());
  const bogoStatsUrl = staticData['bogoStatsUrl'];

  // Get initial state from backend and render ReactDOM when data arrives
  $.getJSON(bogoStatsUrl, data => {

    // Sketch settings
    const canvasContainerId = 'sketch-container';
    const canvas = $("#" + canvasContainerId);
    const sketchSettings = {
      containerId:  canvasContainerId,
      canvasWidth:  canvas.width(),
      canvasHeight: canvas.height(),
      spacing:      1.1,
      yPadding:     60,
    }

    ReactDOM.render(
      <Bogo bogoId=             {staticData['bogoId']}
            updateApiUrl=       {bogoStatsUrl}
            activeStateUrl=     {staticData['minimalApiUrl']}
            startDate=          {data['startDate']}
            endDate=            {data['endDate']}
            sequenceLength=     {data['sequenceLength']}
            animationSettings=  {sketchSettings}
            previousUrl=        {data['previousUrl']}
            nextUrl=            {data['nextUrl']}/>,
      document.getElementById('react-root')
    );
  });
}


uiMain();

