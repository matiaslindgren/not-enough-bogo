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
   * @param {string} props.updateApiUrl - JSON API URL to be polled for changes in state.
   * @param {string} props.startDate - When sorting was started.
   * @param {string} props.activeName - Name of the current state.
   * @param {string} props.sequenceLength - Length of the sequence being sorted.
   * @param {string} props.previousUrl - URL for pager previous button.
   * @param {string} props.nextUrl - URL for pager next button.
   */
  constructor(props) {
    super(props);
    this.state = {
      stateName:    "Loading...",
      endDate:      "Loading...",
      currentSpeed: "Loading..."
    };
  }

  /**
   * If the state is not "Sorted", set timer for calling refreshState.
   * Else, do nothing.
   */
  componentDidMount() {
    if (this.state.stateName === "Sorted") {
      return;
    }

    // TODO the lambda is redundant? test
    this.timerID = setInterval(_ => this.refreshState(), 1000);
  }

  /** Remove refreshState timer. */
  componentWillUnmount() {
    clearInterval(this.timerID);
  }

  /**
   * Make a GET-request to this.props.updateApiUrl and update own state.
   * If returned state is "Sorted", stop polling this.props.updateApiUrl.
   */
  refreshState() {
    const updateApiUrl = this.props.updateApiUrl;
    // Update own state with the current state of the backend
    // A non-null end date signifies the sorting has ended
    $.getJSON(updateApiUrl, data => {

      let changedState;

      if (data.endDate) {
        this.componentWillUnmount();
        changedState = {
          stateName: "Sorted",
          endDate: data.endDate,
          currentSpeed: "-"
        }
      }
      else {
        changedState = {
          stateName: this.props.activeName,
          endDate: "Maybe some day",
          currentSpeed: Math.round(data.currentSpeed) + " shuffles per second"
        }
      }

      this.setState(Object.assign(data, changedState));
    });
  }

  /** Render this component with a Table and Pager. */
  render() {
    return (
      <div>
        <Table stateName={this.state.stateName}
               startDate={this.props.startDate}
               endDate={this.state.endDate}
               sequenceLength={this.props.sequenceLength}
               currentSpeed={this.state.currentSpeed} />
        <Pager previousUrl={this.props.previousUrl}
               nextUrl={this.props.nextUrl}/>
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
          {props.previousUrl.length > 0 &&
            <li className="previous">
              <a href={props.previousUrl}><span aria-hidden="true">&larr;</span> Older</a>
            </li>}
          {props.nextUrl.length > 0 &&
            <li className="next">
              <a href={props.nextUrl}>Newer <span aria-hidden="true">&rarr;</span></a>
            </li>}
        </ul>
      </nav>
    </div>
  );
}


/** Return a random string prefixed by 'Bogosorting '. The random string may or may not be funny.  */
function generateActiveName() {
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


/** Call ReactDOM.render and renders all components. */
function uiMain() {
  const STATIC_DATA = JSON.parse($("#bogo-data-api").html());

  ReactDOM.render(
    <Bogo updateApiUrl={STATIC_DATA["bogoStatsUrl"]}
          startDate={STATIC_DATA['startDate']}
          activeName={generateActiveName()}
          sequenceLength={STATIC_DATA['sequenceLength']}
          previousUrl={STATIC_DATA['previousUrl']}
          nextUrl={STATIC_DATA['nextUrl']}/>,
    document.getElementById('react-root')
  );
}


uiMain();

