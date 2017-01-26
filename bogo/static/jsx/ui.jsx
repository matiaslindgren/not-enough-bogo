import React from 'react';
import ReactDOM from 'react-dom';

class Bogo extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      stateName:    "Loading...",
      endDate:      "Loading...",
      currentSpeed: "Loading..."
    };
  }

  componentDidMount() {
    if (this.state.stateName === "Sorted") {
      return;
    }

    // TODO the lambda is redundant? test
    this.timerID = setInterval(_ => this.refreshState(), 1000);
  }

  componentWillUnmount() {
    clearInterval(this.timerID);
  }

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

  render() {
    return (
      <div>
        <Animation />
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


function Row(props) {
  return (
    <tr>
      <td className="col-xs-4">{props.label}</td>
      <td className="col-xs-8">{props.value}</td>
    </tr>
  );
}


class Animation extends React.Component {
  render() {
    return (



    );
  }
}


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
