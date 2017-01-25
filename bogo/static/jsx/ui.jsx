import React from 'react';
import ReactDOM from 'react-dom';

class Statistics extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      stateName:    "Loading...",
      currentSpeed: "Loading..."
    };
  }

  componentDidMount() {
    if (this.state.stateName === "Sorted") {
      // Statistics loaded for page with sorted sequence, don't refresh
      return;
    }

    this.timerID = setInterval(_ => this.refreshState(), 1000);
  }

  componentWillUnmount() {
    clearInterval(this.timerID);
  }

  refreshState() {
    const jsonURL = this.props.jsonURL;
    // Update own state with the current state of the backend
    $.getJSON(jsonURL, data => {
      const newState = Object.assign(
        data,
        (data.endDate) ?
          { stateName: "Sorted", currentSpeed: "-" } :
          { stateName: this.props.activeName, currentSpeed: Math.round(data.currentSpeed) + " shuffles per second" }
      );
      this.setState(newState);

      if (data.endDate)
        this.componentWillUnmount();
    });
  }

  render() {
    return (
      <div>
        <table className="table table-bordered table-condensed">
          <tbody>
            <Row label="State"               value={this.state.stateName} />
            <Row label="Sorting started at"  value={this.props.startDate} />
            <Row label="Sorting finished at" value={this.state.endDate} />
            <Row label="Sequence length"     value={this.props.sequenceLength} />
            <Row label="Current speed"       value={this.state.currentSpeed} />
          </tbody>
        </table>
      </div>
    );
  }
}


function Row(props) {
  return (
    <tr>
      <td className="col-xs-4">{props.label}</td>
      <td className="col-xs-8">{props.value}</td>
    </tr>
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
    "furiously",
    "with white shores and green fields in mind",
  ];
 return "Bogosorting " + states[Math.floor(Math.random()*states.length)];
}


const STATIC_DATA = JSON.parse($("#bogo-data-api").html());

ReactDOM.render(
  <Statistics jsonURL={STATIC_DATA["bogoStatsUrl"]}
              startDate={STATIC_DATA['startDate']}
              activeName={generateActiveName()}
              sequenceLength={STATIC_DATA['sequenceLength']}/>,
  document.getElementById('react-root')
);
