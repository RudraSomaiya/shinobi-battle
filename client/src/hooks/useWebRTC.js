import { useEffect, useRef, useState, useCallback } from 'react';
import { ICE_SERVERS } from '../utils/constants';
import { MessageType } from '../utils/messageTypes';

/**
 * WebRTC hook for peer-to-peer video streaming.
 * Uses WebSocket for signaling (offer/answer/ICE).
 */
export function useWebRTC(wsSend, playerId, isInitiator) {
  const pcRef = useRef(null);
  const localStreamRef = useRef(null);
  const [localStream, setLocalStream] = useState(null);
  const [remoteStream, setRemoteStream] = useState(null);
  const [rtcConnected, setRtcConnected] = useState(false);

  // Initialize local media
  const startLocalStream = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      });
      localStreamRef.current = stream;
      setLocalStream(stream);
      return stream;
    } catch (err) {
      console.error('[WebRTC] Camera access denied:', err);
      return null;
    }
  }, []);

  // Create peer connection
  const createPeerConnection = useCallback(() => {
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    pcRef.current = pc;

    // Add local tracks
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => {
        pc.addTrack(track, localStreamRef.current);
      });
    }

    // Handle remote stream
    pc.ontrack = (event) => {
      console.log('[WebRTC] Remote track received');
      setRemoteStream(event.streams[0]);
    };

    // Send ICE candidates
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        wsSend({
          type: MessageType.RTC_ICE_CANDIDATE,
          player_id: playerId,
          candidate: event.candidate.toJSON(),
        });
      }
    };

    pc.onconnectionstatechange = () => {
      console.log('[WebRTC] State:', pc.connectionState);
      setRtcConnected(pc.connectionState === 'connected');
    };

    return pc;
  }, [wsSend, playerId]);

  // Create and send offer
  const createOffer = useCallback(async () => {
    const pc = createPeerConnection();
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    wsSend({
      type: MessageType.RTC_OFFER,
      player_id: playerId,
      sdp: pc.localDescription.toJSON(),
    });
  }, [createPeerConnection, wsSend, playerId]);

  // Handle incoming signaling messages
  const handleSignaling = useCallback(async (data) => {
    if (data.type === MessageType.RTC_OFFER && data.player_id !== playerId) {
      // Got offer → create answer
      const pc = createPeerConnection();
      await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      wsSend({
        type: MessageType.RTC_ANSWER,
        player_id: playerId,
        sdp: pc.localDescription.toJSON(),
      });
    } else if (data.type === MessageType.RTC_ANSWER && data.player_id !== playerId) {
      // Got answer
      if (pcRef.current) {
        await pcRef.current.setRemoteDescription(new RTCSessionDescription(data.sdp));
      }
    } else if (data.type === MessageType.RTC_ICE_CANDIDATE && data.player_id !== playerId) {
      // Got ICE candidate
      if (pcRef.current) {
        await pcRef.current.addIceCandidate(new RTCIceCandidate(data.candidate));
      }
    }
  }, [createPeerConnection, wsSend, playerId]);

  // Cleanup
  useEffect(() => {
    return () => {
      pcRef.current?.close();
      localStreamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return {
    localStream,
    remoteStream,
    rtcConnected,
    startLocalStream,
    createOffer,
    handleSignaling,
  };
}
