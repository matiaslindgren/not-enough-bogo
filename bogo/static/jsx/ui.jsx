import React from 'react';
import ReactDOM from 'react-dom';

// TODO this is still a mess, state should be lifted


function factorial(x) {
  return (x === 0) ? 1 : x*factorial(x-1);
}
const SORT_PROBABILITY = _.object(_.map(_.range(1, 30), x => [x, 1.0/factorial(x)]));

/**
 * React component. The top-level component containing all elements on the page with non-static state.
 * @extends React.Component
 */
class BogoController extends React.Component {
  /**
   * Create Bogo with state variables set to "Loading...".
   * @param {Object} props
   * @param {Object} props.initState - Initial state as returned by the backend.
   * etc etc TODO
   */
  constructor(props) {
    super(props);

    const isSorted = props.endDate && props.endDate.length > 0;

    this.state = {
      stateName:       (isSorted) ? "Sorted" : this.generateActiveName(),
      stateNameDots:   "",
      previousUrl:     props.backend.previous,
      nextUrl:         props.backend.next
    }

    const animationSettings = {
      containerId: props.sketchContainerId,
      columns:     props.sequenceLength,
      shufflin:    !isSorted
    }

    this.animationWrapper = new AnimationWrapper(animationSettings);

    // Trigger a GET request for full state update
    this.refreshState();
  }

  /** Return a random string prefixed with 'Bogosorting '. The random string may or may not be funny.  */
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

  componentDidMount() {
    if (this.state.stateName !== "Sorted") {
      this.timerID = setInterval(
        _ => this.refreshState(),
        this.props.backend.maxPollingInterval
      );
    }

    // Start animation
    let p5app = new p5(this.animationWrapper.p5sketch());
    // hi, my name is hacky hackerpants and this is hack-ass
    const redrawUntilNoErrors = function(t) {
      try {
        // Trigger redraw
        p5app.windowResized();
      } catch(err) {
        // Something was missing and everything exploded,
        // try again after 2t ms.
        const t2 = 2*t;
        setTimeout(_ => redrawUntilNoErrors(t2), t2);
      }
    }
    redrawUntilNoErrors(10);
  }

  /** The sequence is sorted, stop refresh timer. */
  componentWillUnmount() {
    clearInterval(this.timerID);
    this.animationWrapper.stopShuffling();
  }

  refreshState() {
    const activeStateUrl = this.props.backend.activeStateUrl;
    // Retrieve current state
    $.getJSON(activeStateUrl, data => {
      // If the returned state id is different from this Bogo,
      // the sequence has been sorted in the backend.
      if (data.activeId !== this.props.backend.bogoId) {
        this.componentWillUnmount();
        // Retrieve full statistics for this Bogo and stop everything.
        $.getJSON(this.props.backend.bogoStatsUrl, fullData => {
          this.setState({
            stateName:       "Sorted",
            stateNameDots:   "",
            endDate:         fullData.data.endDate,
            totalIterations: fullData.data.totalIterations,
            currentSpeed:    "-",
            previousUrl:     fullData.links.previous,
            nextUrl:         fullData.links.next
          });
        });
      }
      else {
        // The sequence is still being sorted, update speed and dots in title
        const currentSuffix = this.state.stateNameDots;
        this.setState({
          currentSpeed:    data.currentSpeed,
          stateNameDots:   currentSuffix.length < 4 ? currentSuffix + "." : " ",
          totalIterations: data.totalIterations,
        });
      }
    });
  }

  /** Render the whole mess. */
  render() {
    return (
      <Bogo stateName=      {this.state.stateName}
            stateNameSuffix={this.state.stateNameDots}
            startDate=      {this.props.startDate}
            endDate=        {this.state.endDate}
            sequenceLength= {this.props.sequenceLength}
            currentSpeed=   {this.state.currentSpeed}
            totalIterations={this.state.totalIterations}
            previousUrl=    {this.state.previousUrl}
            nextUrl=        {this.state.nextUrl}
      />
    );
  }
}


class Bogo extends React.Component {
  render() {
    return (
      <div className="container">
        <div id="bogo-title-container">
          <h4>{this.props.stateName}<span>{this.props.stateNameSuffix}</span></h4>
        </div>
        <div className="container" id="sketch-container"></div>
        <Table startDate=       {this.props.startDate}
               endDate=         {this.props.endDate}
               sequenceLength=  {this.props.sequenceLength}
               currentSpeed=    {this.props.currentSpeed}
               totalIterations= {this.props.totalIterations}
        />
        <Pager previousUrl=    {this.props.previousUrl}
               nextUrl=        {this.props.nextUrl}
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
  const startDateString = (props.startDate) ? new Date(props.startDate).toString() : "";
  const endDateString = (props.endDate) ? new Date(props.endDate).toString() : "";

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
            <Row label="Sequence length" value={props.sequenceLength} />
            {(!props.endDate && props.currentSpeed) &&
              <TooltipRow
                label="Current speed"
                value={Math.round(props.currentSpeed) + " shuffles per second"}
                tooltip="The actual amount of iterations at the server right now"/>
            }
            <Row label="Total amount of shuffles" value={props.totalIterations} />
            <TooltipRow
                label="Sort probability"
                value={SORT_PROBABILITY[props.sequenceLength]}
                tooltip="Assuming equal probability for generating any permutation"/>
            <Row label="Sorting started at" value={startDateString} />
            <Row label="Sorting finished at " value={endDateString} />
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
      <td>{props.label}</td>
      <td>{props.value}</td>
    </tr>
  );
}


function TooltipRow(props) {
  return (
    <tr data-toggle="tooltip"
        data-placement="bottom"
        title={props.tooltip}>
      <td>{props.label}</td>
      <td>{props.value}</td>
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
  const backendData = JSON.parse($("#bogo-data-api").html());
  const bogoStatsUrl = backendData.bogoStatsUrl;
  const sketchContainerId = "#sketch-container";

  // Get initial state from backend and render ReactDOM when data arrives
  $.getJSON(bogoStatsUrl, state => {

    ReactDOM.render(
      <BogoController
            startDate=        {state.data.startDate}
            endDate=          {state.data.endDate}
            sequenceLength=   {state.data.sequenceLength}
            backend=          {Object.assign({}, backendData, state.links)}
            sketchContainerId={sketchContainerId}
        />,
      document.getElementById('react-root')
    );
  });
}


uiMain();

