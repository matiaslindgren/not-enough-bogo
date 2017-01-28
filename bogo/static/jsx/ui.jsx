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
   * @param {string} props.updateApiUrl - URL for full statistics, should be considered slow.
   * @param {string} props.activeStateUrl - JSON API URL to be polled for changes in state.
   * @param {string} props.startDate - Date when sorting was started.
   * @param {string} props.endDate - (Optional) Date when sorting ended. NOTE: the presence of this parameter means the sequence should be considered sorted.
   * @param {string} props.iterations - (Optional) Amount of total iterations used before sequence was sorted.
   * @param {string} props.stopAnimationHandle
   * @param {string} props.previousUrl - URL for pager previous button.
   * @param {string} props.nextUrl - URL for pager next button.
   */
   constructor(props) {
     super(props);

     let initState;
     const shufflin = props.endDate === null || props.endDate === undefined;

     if (shufflin) {
       initState = {
         stateName: this.generateActiveName(),
         endDate: "Maybe some day",
         currentSpeed: "Loading...",
         totalIterations: "Loading..."
       }
     }
     else {
       initState = {
         stateName: "Sorted",
         endDate: props.endDate,
         currentSpeed: "-",
         totalIterations: props.iterations
       }
     }
     this.state = Object.assign(
       initState,
       { stateNameSuffix: " ",
         previousUrl: this.props.previousUrl,
         nextUrl: this.props.nextUrl,
       }
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

  /** If the state is not "Sorted", set timer for calling refreshState. */
  componentDidMount() {
    if (this.state.stateName !== "Sorted")
      this.timerID = setInterval(_ => this.refreshState(), 1000);
    //this.refreshState(); //TODO
  }

  /** The sequence is sorted, stop refresh timer. */
  componentWillUnmount() {
    if (this.timerID)
      clearInterval(this.timerID);
    this.props.stopAnimationHandle();
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
            stateName:       "Sorted",
            stateNameSuffix: "",
            endDate:         fullData.endDate,
            totalIterations: fullData.totalIterations,
            currentSpeed:    "-",
            previousUrl:     fullData.previousUrl,
            nextUrl:         fullData.nextUrl
          });
        });
      }
      else {
        // The sequence is still being sorted, update speed and dots in title
        const currentSuffix = this.state.stateNameSuffix;
        this.setState({
          currentSpeed:    Math.round(data.currentSpeed) + " shuffles per second",
          stateNameSuffix: currentSuffix.length < 4 ? currentSuffix + "." : " ",
          totalIterations: data.totalIterations,
        });
      }
    });
  }

  /** Render the whole mess. */
  render() {
    return (
      <div className="container">
        <div id="bogo-title-container">
          <h4>{this.state.stateName}<span>{this.state.stateNameSuffix}</span></h4>
        </div>
        <div className="container" id="sketch-container"></div>
        <Table startDate=      {this.props.startDate}
               endDate=        {this.state.endDate}
               sequenceLength= {this.props.sequenceLength}
               currentSpeed=   {this.state.currentSpeed}
               totalIterations={this.state.totalIterations}
        />
        <Pager previousUrl=    {this.state.previousUrl}
               nextUrl=        {this.state.nextUrl}
        />
      </div>
    );
  }
}



/**
 * React component. A collapsable Table containing Row-components.
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
      <div className="container" id="collapse-toggle-container">
        <button className="btn btn-default btn-xs"
                id="collapse-toggle"
                type="button"
                data-toggle="collapse"
                data-target="#statistics-collapse"
                aria-expanded="false"
                aria-controls="statistics-collapse">
        Data go away
        </button>
      </div>
      <div className="collapse in" id="statistics-collapse">
        <table className="table table-hover table-condensed">
          <tbody>
            <Row label="Current speed"       value={props.currentSpeed} />
            <Row label="Sequence length"     value={props.sequenceLength} />
            <Row label="Sorting started at"  value={props.startDate} />
            <Row label="Sorting finished at" value={props.endDate} />
            <Row label="Total amount of shuffles" value={props.totalIterations} />
          </tbody>
        </table>
      </div>
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
      <td className="col-xs-6">{props.label}</td>
      <td className="col-xs-6">{props.value}</td>
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
  const bogoStatsUrl = staticData.bogoStatsUrl;

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
      shufflin:     data.endDate === null || data.endDate === undefined,
      columns:      data.sequenceLength,
    }

    const animation = new SequenceSketch(sketchSettings);

    ReactDOM.render(
      <Bogo bogoId=             {staticData.bogoId}
            updateApiUrl=       {bogoStatsUrl}
            activeStateUrl=     {staticData.minimalApiUrl}
            startDate=          {data.startDate}
            endDate=            {data.endDate}
            iterations=         {data.totalIterations}
            sequenceLength=     {data.sequenceLength}
            stopAnimationHandle={(_ => animation.stopShuffling())}
            previousUrl=        {data.previousUrl}
            nextUrl=            {data.nextUrl}/>,
      document.getElementById('react-root')
    );

    let p5app = new p5(animation.p5sketch());
    // hi, my name is hacky hackerpants and this is hack-ass
    const redrawUntilNoErrors = function(t) {
      try {
        // Trigger redraw
        p5app.windowResized();
      } catch(err) {
        // Something was missing and everything exploded,
        // try again after 2t ms.
        setTimeout(redrawUntilNoErrors, 2*t);
      }
      // Nothing exploded, recursion stops
    }
    redrawUntilNoErrors(10);
  });
}


uiMain();

