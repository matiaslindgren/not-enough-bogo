import React from 'react';
import ReactDOM from 'react-dom';


class Statistics extends React.Component {
  componentDidMount() {
    if (!this.state.endDate)
      this.timerID = setInterval(_ => this.refreshState(), 1000);
  }

  componentWillUnmount() {
    if (this.timerID)
      clearInterval(this.timerID);
  }

  refreshState() {
    // Retrieve url to statistics resource rendered by the backend
    const JSONPath = JSON.parse($("#bogo-data-api").html())['bogoStatsUrl'];
    // Update this state with backend state
    $.getJSON(JSONPath, data => this.setState(data));
  }

  render() {
    return (
      <div>
        <table className="table table-condensed">
          <tbody>
            <Row label="Sorting started"  value={this.state.startDate} />
            <Row label="Sorting finished" value={this.state.endDate} />
            <Row label="Sequence length"  value={this.state.sequenceLength} />
            <Row label="Current speed"    value={Math.round(this.state.currentSpeed) + " shuffles per second"} />
          </tbody>
        </table>
      </div>
    );
  }
}


function Row(props) {
  return (
    <tr>
      <td>{props.label}</td>
      <td>{props.value}</td>
    </tr>
  );
}


ReactDOM.render(
  <Statistics />,
  document.getElementById('react-root')
);
